"""Tests for portfolio metrics calculation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from portfolio.metrics import (
    compute_basic_trade_stats,
    period_stats,
    reconstruct_closed_trades_from_fills,
)


def test_compute_basic_trade_stats_empty():
    """Test stats calculation with empty trades."""
    df = pd.DataFrame(columns=["pnl"])
    stats = compute_basic_trade_stats(df)
    assert stats["num_trades"] == 0
    assert stats["win_rate"] == 0.0
    assert stats["avg_payout"] == 0.0


def test_compute_basic_trade_stats_with_trades():
    """Test stats calculation with winning and losing trades."""
    df = pd.DataFrame({
        "pnl": [100.0, -50.0, 200.0, -30.0, 150.0],
    })
    stats = compute_basic_trade_stats(df)
    assert stats["num_trades"] == 5
    assert stats["win_rate"] == 0.6  # 3 wins / 5 total
    # Avg win = (100 + 200 + 150) / 3 = 150
    # Avg loss = (50 + 30) / 2 = 40
    # Payout = 150 / 40 = 3.75
    assert abs(stats["avg_payout"] - 3.75) < 0.01


def test_period_stats_1d():
    """Test period stats calculation for daily period."""
    now = datetime.now()
    dates = [now - timedelta(days=i) for i in range(10, -1, -1)]
    equity_values = [1000.0 * (1.01 ** i) for i in range(11)]
    df = pd.DataFrame({
        "ts": dates,
        "equity": equity_values,
    })
    stats = period_stats(df, period="1D")
    assert "return" in stats
    assert "max_dd" in stats


def test_period_stats_empty():
    """Test period stats with empty data."""
    df = pd.DataFrame(columns=["ts", "equity"])
    stats = period_stats(df, period="1D")
    assert stats["return"] == 0.0
    assert stats["max_dd"] == 0.0


def test_reconstruct_closed_trades_simple():
    """Test reconstructing closed trades from fills."""
    now = datetime.now(timezone.utc)
    fills = pd.DataFrame({
        "ts": [now, now + timedelta(minutes=10)],
        "symbol": ["BTCUSDT", "BTCUSDT"],
        "qty": [1.0, -1.0],  # Buy then sell
        "price": [50_000.0, 55_000.0],
        "commission": [10.0, 11.0],
    })
    trades = reconstruct_closed_trades_from_fills(fills)
    assert len(trades) == 1
    assert trades.iloc[0]["symbol"] == "BTCUSDT"
    assert trades.iloc[0]["entry_price"] == 50_000.0
    assert trades.iloc[0]["exit_price"] == 55_000.0
    # PnL = (55000 - 50000) * 1 - 10 - 11 = 4979
    assert abs(trades.iloc[0]["pnl"] - 4979.0) < 1.0


def test_reconstruct_closed_trades_partial():
    """Test partial position closing."""
    now = datetime.now(timezone.utc)
    fills = pd.DataFrame({
        "ts": [now, now + timedelta(minutes=10)],
        "symbol": ["BTCUSDT", "BTCUSDT"],
        "qty": [2.0, -1.0],  # Buy 2, sell 1
        "price": [50_000.0, 55_000.0],
        "commission": [20.0, 11.0],
    })
    trades = reconstruct_closed_trades_from_fills(fills)
    assert len(trades) == 1
    assert trades.iloc[0]["qty"] == 1.0  # Only 1 unit closed


def test_reconstruct_closed_trades_empty():
    """Test reconstruct with empty fills."""
    df = pd.DataFrame(columns=["ts", "symbol", "qty", "price", "commission"])
    trades = reconstruct_closed_trades_from_fills(df)
    assert isinstance(trades, pd.DataFrame)
    assert len(trades) == 0

