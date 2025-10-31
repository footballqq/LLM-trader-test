from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class FillRecord:
    ts: datetime
    symbol: str
    qty: float  # 买入为正，卖出为负
    price: float
    commission: float


@dataclass
class PortfolioState:
    cash: float = 1_000_000.0
    positions: Dict[str, float] = field(default_factory=dict)
    last_price: Dict[str, float] = field(default_factory=dict)
    fills: List[FillRecord] = field(default_factory=list)

    def mark_price(self, symbol: str, price: float) -> None:
        self.last_price[symbol] = price

    def get_last_price(self, symbol: str) -> Optional[float]:
        return self.last_price.get(symbol)

    def apply_fill(self, symbol: str, price: float, signed_qty: float, commission: float, ts: datetime) -> None:
        position = self.positions.get(symbol, 0.0)
        self.positions[symbol] = position + signed_qty
        self.cash -= price * signed_qty + commission
        self.fills.append(FillRecord(ts=ts, symbol=symbol, qty=signed_qty, price=price, commission=commission))

    def equity(self) -> float:
        total = self.cash
        for symbol, qty in self.positions.items():
            price = self.last_price.get(symbol)
            if price is not None and not pd.isna(price):
                total += qty * float(price)
        return float(total)

    def realized_pnl(self) -> float:
        # 简化：以现金变动相对初始现金衡量；更严格的实现可引入持仓成本与平仓盈亏。
        if not self.fills:
            return 0.0
        # 这里不记录初始现金，外层可持有基线
        return 0.0

    def to_dataframe(self) -> pd.DataFrame:
        if not self.fills:
            return pd.DataFrame(columns=["ts", "symbol", "qty", "price", "commission"]).astype(
                {"ts": "datetime64[ns]", "symbol": "string", "qty": "float64", "price": "float64", "commission": "float64"}
            )
        return pd.DataFrame([f.__dict__ for f in self.fills])


