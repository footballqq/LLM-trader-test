from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class Order:
    order_id: str
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    price: Optional[float] = None
    type: str = "market"  # market | limit
    ts: Optional[datetime] = None


@dataclass
class Fill:
    order_id: str
    symbol: str
    qty: float
    price: float
    commission: float
    ts: datetime


class ExecutionProvider(ABC):
    """抽象的执行层接口，可对接交易所或纸上撮合。"""

    @abstractmethod
    def send_order(self, order: Order) -> Fill:
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> None:
        return None

    @abstractmethod
    def query_positions(self) -> Dict[str, float]:
        raise NotImplementedError


