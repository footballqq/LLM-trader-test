from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from ..market.interfaces import MarketDataProvider
from ..market.a_share_wind import AShareWindMarketDataProvider
from ..market.crypto_binance import CryptoBinanceMarketDataProvider
from ..execution.interfaces import ExecutionProvider
from ..execution.paper_trader import PaperTrader, PaperConfig
from ..portfolio.portfolio_state import PortfolioState


@dataclass
class AppContext:
    cfg: Dict[str, Any]
    market: MarketDataProvider
    execution: ExecutionProvider
    portfolio: PortfolioState


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_context(config_path: str = "config/settings.example.yaml") -> AppContext:
    cfg = load_yaml(config_path)

    market_cfg = cfg.get("market", {})
    storage_cfg = cfg.get("storage", {})
    ui_cfg = cfg.get("ui", {})
    trading_cfg = cfg.get("trading", {})

    market_type = str(market_cfg.get("type", "a_share")).lower()
    provider = str(market_cfg.get("provider", "wind")).lower()

    data_dir = storage_cfg.get("data_dir", "data")

    # Market provider
    if market_type == "a_share" and provider == "wind":
        market: MarketDataProvider = AShareWindMarketDataProvider(
            data_dir=data_dir,
            cache=bool(storage_cfg.get("cache", True)),
        )
    elif market_type == "crypto" and provider in {"binance", "crypto_binance"}:
        api_key = cfg.get("binance", {}).get("api_key")
        api_secret = cfg.get("binance", {}).get("api_secret")
        market = CryptoBinanceMarketDataProvider(api_key=api_key, api_secret=api_secret)
    else:
        # 默认回退到 A股-Wind（若无 Wind 环境会降级为空数据）
        market = AShareWindMarketDataProvider(
            data_dir=data_dir,
            cache=bool(storage_cfg.get("cache", True)),
        )

    # Portfolio and Execution
    portfolio = PortfolioState(cash=float(cfg.get("initial_cash", 1_000_000)))
    paper_conf = PaperConfig(
        slippage_bps=float(trading_cfg.get("slippage_bps", 0.0)),
        slippage_abs=float(trading_cfg.get("slippage_abs", 0.0)),
        commission_rate=float(trading_cfg.get("commission", 0.0)),
        commission_per_lot=float(trading_cfg.get("commission_per_lot", 0.0)),
    )
    execution: ExecutionProvider = PaperTrader(portfolio=portfolio, config=paper_conf)

    return AppContext(cfg=cfg, market=market, execution=execution, portfolio=portfolio)


