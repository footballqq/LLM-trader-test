from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Optional

import pandas as pd

from ..market.interfaces import MarketDataProvider
from ..execution.interfaces import Order
from ..execution.paper_trader import PaperTrader
from ..portfolio.portfolio_state import PortfolioState


DecisionFn = Callable[[pd.DataFrame], Optional[Order]]


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame


def run_simple_backtest(
    market: MarketDataProvider,
    trader: PaperTrader,
    symbol: str,
    freq: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    decision_fn: Optional[DecisionFn] = None,
) -> BacktestResult:
    ohlcv = market.load_ohlcv(symbol=symbol, freq=freq, start=start, end=end)
    if ohlcv.empty:
        return BacktestResult(equity_curve=pd.DataFrame(columns=["ts", "equity"]))

    portfolio: PortfolioState = trader.portfolio
    equities = []

    for _, row in ohlcv.iterrows():
        ts = pd.to_datetime(row["datetime"]).to_pydatetime()
        price = float(row["close"])
        portfolio.mark_price(symbol, price)

        if decision_fn is not None:
            order = decision_fn(ohlcv.loc[: _, :])  # 传入至当前K线的切片
            if order is not None:
                trader.send_order(order)

        equities.append({"ts": ts, "equity": portfolio.equity()})

    eq_df = pd.DataFrame(equities)
    return BacktestResult(equity_curve=eq_df)


