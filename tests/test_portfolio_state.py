"""Tests for portfolio state management."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from portfolio.portfolio_state import PortfolioState


def test_portfolio_initialization():
    """Test portfolio initializes with default cash."""
    p = PortfolioState()
    assert p.cash == 1_000_000.0
    assert len(p.positions) == 0
    assert len(p.fills) == 0


def test_portfolio_custom_cash():
    """Test portfolio with custom initial cash."""
    p = PortfolioState(cash=500_000.0)
    assert p.cash == 500_000.0


def test_mark_price():
    """Test marking latest price for a symbol."""
    p = PortfolioState()
    p.mark_price("BTCUSDT", 50000.0)
    assert p.get_last_price("BTCUSDT") == 50000.0


def test_apply_fill_buy():
    """Test applying a buy fill."""
    p = PortfolioState(cash=100_000.0)
    ts = datetime.now(timezone.utc)
    p.apply_fill("BTCUSDT", price=50_000.0, signed_qty=1.0, commission=10.0, ts=ts)
    assert p.positions["BTCUSDT"] == 1.0
    assert p.cash == 100_000.0 - 50_000.0 - 10.0
    assert len(p.fills) == 1


def test_apply_fill_sell():
    """Test applying a sell fill."""
    p = PortfolioState(cash=100_000.0)
    ts = datetime.now(timezone.utc)
    # First buy
    p.apply_fill("BTCUSDT", price=50_000.0, signed_qty=1.0, commission=10.0, ts=ts)
    # Then sell
    p.apply_fill("BTCUSDT", price=55_000.0, signed_qty=-0.5, commission=5.0, ts=ts)
    assert p.positions["BTCUSDT"] == 0.5
    assert p.cash == 100_000.0 - 50_000.0 - 10.0 + 27_500.0 - 5.0


def test_equity_calculation():
    """Test equity calculation with positions."""
    p = PortfolioState(cash=100_000.0)
    p.mark_price("BTCUSDT", 50_000.0)
    ts = datetime.now(timezone.utc)
    p.apply_fill("BTCUSDT", price=50_000.0, signed_qty=1.0, commission=10.0, ts=ts)
    # Equity = cash + position_value
    expected_equity = 100_000.0 - 50_000.0 - 10.0 + 1.0 * 50_000.0
    assert abs(p.equity() - expected_equity) < 0.01


def test_to_dataframe():
    """Test converting fills to DataFrame."""
    p = PortfolioState()
    ts = datetime.now(timezone.utc)
    p.apply_fill("BTCUSDT", price=50_000.0, signed_qty=1.0, commission=10.0, ts=ts)
    df = p.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "symbol" in df.columns
    assert df.iloc[0]["symbol"] == "BTCUSDT"


def test_empty_portfolio_to_dataframe():
    """Test empty portfolio DataFrame."""
    p = PortfolioState()
    df = p.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert "ts" in df.columns or len(df) == 0

