from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from .interfaces import MarketDataProvider
import importlib

try:
    # Wind 环境可能不可用，按需降级
    from WindPy import w  # type: ignore
    _WIND_AVAILABLE = True
except Exception:  # pragma: no cover - 环境降级
    w = None
    _WIND_AVAILABLE = False


class AShareWindMarketDataProvider(MarketDataProvider):
    """
    通过 Wind 拉取 A股/股指期货分钟线。
    - 统一输出列：datetime, open, high, low, close, volume
    - 本地缓存：data_dir/market_cache/{symbol}_{freq}.parquet
    """

    def __init__(self, data_dir: str = "data", cache: bool = True) -> None:
        self.data_dir = Path(data_dir)
        self.cache = cache
        self.cache_dir = self.data_dir / "market_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if _WIND_AVAILABLE:
            try:
                w.start()
            except Exception:
                pass

    def _cache_path(self, symbol: str, freq: str) -> Path:
        safe_symbol = symbol.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{safe_symbol}_{freq}.parquet"

    def _read_cache(self, path: Path) -> Optional[pd.DataFrame]:
        if not path.exists():
            return None
        try:
            df = pd.read_parquet(path)
            return df
        except Exception:
            return None

    def _write_cache(self, path: Path, df: pd.DataFrame) -> None:
        try:
            df.to_parquet(path)
        except Exception:
            pass

    def load_ohlcv(
        self,
        symbol: str,
        freq: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        # 先尝试缓存
        cache_path = self._cache_path(symbol, freq)
        if self.cache:
            cached = self._read_cache(cache_path)
            if cached is not None:
                df = cached
                if start is not None:
                    df = df[df["datetime"] >= pd.Timestamp(start)]
                if end is not None:
                    df = df[df["datetime"] <= pd.Timestamp(end)]
                if limit is not None and len(df) > limit:
                    df = df.tail(limit)
                return df.reset_index(drop=True)

        if not _WIND_AVAILABLE:
            # 无 Wind 环境时返回空 DataFrame，占位避免上层报错
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

        # 分钟线优先：使用 wsi；否则尝试对接 data_provider.WindDataProvider（日线 close 序列）
        if str(freq).endswith("m"):
            period_map = {
                "1m": "1",
                "5m": "5",
                "15m": "15",
                "30m": "30",
                "60m": "60",
            }
            wind_period = period_map.get(freq, "1")

            start_str = start.strftime("%Y-%m-%d %H:%M:%S") if start else None
            end_str = end.strftime("%Y-%m-%d %H:%M:%S") if end else None
            options = f"PriceAdj=F;Fill=Previous;BarSize={wind_period};TradingCalendar=ChinaSSE"

            try:
                resp = w.wsi(symbol, "open,high,low,close,volume", start_str, end_str, options)  # type: ignore[attr-defined]
            except Exception:
                return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

            if not resp or not resp.Times or not resp.Data:
                return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

            df = pd.DataFrame(
                {
                    "datetime": pd.to_datetime(resp.Times),
                    "open": resp.Data[0],
                    "high": resp.Data[1],
                    "low": resp.Data[2],
                    "close": resp.Data[3],
                    "volume": resp.Data[4],
                }
            )

            if limit is not None and len(df) > limit:
                df = df.tail(limit)

            df = df.dropna().reset_index(drop=True)

            if self.cache and not df.empty:
                self._write_cache(cache_path, df)

            return df

        # 尝试通过 data_provider.WindDataProvider 获取日线 close
        try:
            dp_module = importlib.import_module("data_provider")
            WindDataProvider = getattr(dp_module, "WindDataProvider")
            wp = WindDataProvider()
            import pandas as _pd  # local alias
            start_dt = _pd.Timestamp(start) if start else _pd.Timestamp.now() - _pd.Timedelta(days=365)
            end_dt = _pd.Timestamp(end) if end else _pd.Timestamp.now()
            series = wp.get_data([symbol], start_dt, end_dt)
        except Exception:
            series = pd.DataFrame()

        if series is None or series.empty:
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

        out = pd.DataFrame({
            "datetime": series.index,
            "close": pd.to_numeric(series.iloc[:, 0], errors="coerce"),
        }).dropna()
        out["open"] = out["close"]
        out["high"] = out["close"]
        out["low"] = out["close"]
        out["volume"] = 0.0

        if limit is not None and len(out) > limit:
            out = out.tail(limit)

        out = out.reset_index(drop=True)

        if self.cache and not out.empty:
            self._write_cache(cache_path, out)

        return out


