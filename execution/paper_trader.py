from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from .interfaces import ExecutionProvider, Order, Fill
try:
    from portfolio.portfolio_state import PortfolioState
except ImportError:
    from ..portfolio.portfolio_state import PortfolioState


@dataclass
class PaperConfig:
    slippage_bps: float = 0.0  # 以基点计算的滑点（万分之一）
    slippage_abs: float = 0.0  # 绝对价格滑点
    commission_rate: float = 0.0  # 按成交额比例
    commission_per_lot: float = 0.0  # 每手固定费用（如期货）


class PaperTrader(ExecutionProvider):
    """简单的虚拟撮合：
    - 市价单：以传入成交参考价为基础，施加滑点；
    - 佣金：按比例或每手固定，二者可叠加；
    - 持仓与现金由 PortfolioState 托管。
    """

    def __init__(
        self,
        portfolio: PortfolioState,
        config: Optional[PaperConfig] = None,
    ) -> None:
        self.portfolio = portfolio
        self.config = config or PaperConfig()

    def _apply_slippage(self, price: float, side: str) -> float:
        p = price
        if self.config.slippage_bps:
            delta = p * (self.config.slippage_bps / 10000.0)
            p = p + delta if side == "buy" else p - delta
        if self.config.slippage_abs:
            p = p + self.config.slippage_abs if side == "buy" else p - self.config.slippage_abs
        return max(p, 0.0)

    def _commission(self, price: float, qty: float) -> float:
        cost = 0.0
        if self.config.commission_rate:
            cost += price * qty * self.config.commission_rate
        if self.config.commission_per_lot:
            cost += self.config.commission_per_lot
        return cost

    def send_order(self, order: Order) -> Fill:
        from datetime import timezone
        now = order.ts or datetime.now(timezone.utc)
        ref_price = order.price if order.price is not None else self.portfolio.get_last_price(order.symbol)
        if ref_price is None or pd.isna(ref_price):
            ref_price = 0.0

        exec_price = self._apply_slippage(ref_price, order.side)
        commission = self._commission(exec_price, order.qty)

        signed_qty = order.qty if order.side == "buy" else -order.qty
        self.portfolio.apply_fill(order.symbol, exec_price, signed_qty, commission, now)

        return Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            qty=order.qty,
            price=exec_price,
            commission=commission,
            ts=now,
        )

    def query_positions(self) -> Dict[str, float]:
        return self.portfolio.positions.copy()


