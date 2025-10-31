from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

import pandas as pd


@dataclass(frozen=True)
class TradingSession:
    name: str
    timezone: str
    open_time: str
    close_time: str


class MarketDataProvider(ABC):
    """
    抽象的行情数据提供者。

    统一输出：pd.DataFrame，包含列：datetime, open, high, low, close, volume
    索引或列中必须有 datetime（UTC 或本地时区需通过配置指定）。
    """

    @abstractmethod
    def load_ohlcv(
        self,
        symbol: str,
        freq: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """拉取OHLCV数据，分钟线优先。"""
        raise NotImplementedError

    def subscribe(self, symbols: Iterable[str], freq: str) -> None:
        """可选的订阅接口（本地/实时可实现）。默认不实现。"""
        return None

    def get_calendar(self, symbol: Optional[str] = None) -> Iterable[TradingSession]:
        """返回交易时段/日历定义，默认返回空集合，由上层自行控制时段过滤。"""
        return []


