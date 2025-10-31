from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
from binance.client import Client

from .interfaces import MarketDataProvider


_FREQ_TO_INTERVAL = {
    "1m": Client.KLINE_INTERVAL_1MINUTE,
    "3m": Client.KLINE_INTERVAL_3MINUTE,
    "5m": Client.KLINE_INTERVAL_5MINUTE,
    "15m": Client.KLINE_INTERVAL_15MINUTE,
    "30m": Client.KLINE_INTERVAL_30MINUTE,
    "1h": Client.KLINE_INTERVAL_1HOUR,
}


class CryptoBinanceMarketDataProvider(MarketDataProvider):
    """基于 python-binance 的分钟线拉取，输出统一 OHLCV。"""

    def __init__(self, api_key: str | None = None, api_secret: str | None = None, testnet: bool = False) -> None:
        self.client = Client(api_key or "", api_secret or "", testnet=testnet)

    def load_ohlcv(
        self,
        symbol: str,
        freq: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        interval = _FREQ_TO_INTERVAL.get(freq, Client.KLINE_INTERVAL_1MINUTE)
        start_str = start.strftime("%Y-%m-%d %H:%M:%S") if start else None
        end_str = end.strftime("%Y-%m-%d %H:%M:%S") if end else None

        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, startTime=None, endTime=None, limit=limit or 500)
        except Exception:
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

        if not klines:
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(klines, columns=[
            "open_time","open","high","low","close","volume",
            "close_time","quote_asset_volume","number_of_trades","taker_buy_base","taker_buy_quote","ignore"
        ])
        out = pd.DataFrame({
            "datetime": pd.to_datetime(df["open_time"], unit="ms"),
            "open": pd.to_numeric(df["open"], errors="coerce"),
            "high": pd.to_numeric(df["high"], errors="coerce"),
            "low": pd.to_numeric(df["low"], errors="coerce"),
            "close": pd.to_numeric(df["close"], errors="coerce"),
            "volume": pd.to_numeric(df["volume"], errors="coerce"),
        }).dropna()
        return out.reset_index(drop=True)


