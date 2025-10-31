"""Tests for paper trading execution."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from execution.interfaces import Order
from execution.paper_trader import PaperTrader, PaperConfig
from portfolio.portfolio_state import PortfolioState


def test_paper_trader_initialization():
    """Test paper trader initializes correctly."""
    portfolio = PortfolioState(cash=100_000.0)
    trader = PaperTrader(portfolio=portfolio)
    assert trader.portfolio == portfolio
    assert trader.config.slippage_bps == 0.0
    assert trader.config.commission_rate == 0.0


def test_paper_trader_with_config():
    """Test paper trader with custom config."""
    portfolio = PortfolioState()
    config = PaperConfig(slippage_bps=5.0, commission_rate=0.001)
    trader = PaperTrader(portfolio=portfolio, config=config)
    assert trader.config.slippage_bps == 5.0
    assert trader.config.commission_rate == 0.001


def test_send_market_order_buy():
    """Test sending a market buy order."""
    portfolio = PortfolioState(cash=100_000.0)
    portfolio.mark_price("BTCUSDT", 50_000.0)
    trader = PaperTrader(portfolio=portfolio)
    
    order = Order(
        order_id="test-1",
        symbol="BTCUSDT",
        side="buy",
        qty=1.0,
        price=50_000.0,
        ts=datetime.now(timezone.utc),
    )
    fill = trader.send_order(order)
    
    assert fill.order_id == "test-1"
    assert fill.symbol == "BTCUSDT"
    assert fill.qty == 1.0
    assert fill.price == 50_000.0
    assert portfolio.positions.get("BTCUSDT", 0) == 1.0


def test_send_market_order_with_slippage():
    """Test order execution with slippage."""
    portfolio = PortfolioState(cash=100_000.0)
    portfolio.mark_price("BTCUSDT", 50_000.0)
    config = PaperConfig(slippage_bps=10.0)  # 0.1%
    trader = PaperTrader(portfolio=portfolio, config=config)
    
    order = Order(
        order_id="test-2",
        symbol="BTCUSDT",
        side="buy",
        qty=1.0,
        price=50_000.0,
        ts=datetime.now(timezone.utc),
    )
    fill = trader.send_order(order)
    
    # Buy should have higher price due to slippage
    expected_price = 50_000.0 * 1.001
    assert abs(fill.price - expected_price) < 1.0


def test_send_market_order_with_commission():
    """Test order execution with commission."""
    portfolio = PortfolioState(cash=100_000.0)
    portfolio.mark_price("BTCUSDT", 50_000.0)
    config = PaperConfig(commission_rate=0.001)  # 0.1%
    trader = PaperTrader(portfolio=portfolio, config=config)
    
    order = Order(
        order_id="test-3",
        symbol="BTCUSDT",
        side="buy",
        qty=1.0,
        price=50_000.0,
        ts=datetime.now(timezone.utc),
    )
    fill = trader.send_order(order)
    
    expected_commission = 50_000.0 * 0.001
    assert abs(fill.commission - expected_commission) < 0.01


def test_query_positions():
    """Test querying positions."""
    portfolio = PortfolioState()
    portfolio.mark_price("BTCUSDT", 50_000.0)
    trader = PaperTrader(portfolio=portfolio)
    
    order = Order(
        order_id="test-4",
        symbol="BTCUSDT",
        side="buy",
        qty=2.0,
        price=50_000.0,
        ts=datetime.now(timezone.utc),
    )
    trader.send_order(order)
    
    positions = trader.query_positions()
    assert positions["BTCUSDT"] == 2.0

