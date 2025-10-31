from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .app_context import build_context, AppContext
from ..execution.interfaces import Order


_CTX: Optional[AppContext] = None


def _get_ctx() -> AppContext:
    global _CTX
    if _CTX is None:
        from os import getenv
        cfg_path = getenv("APP_SETTINGS", "config/settings.example.yaml")
        _CTX = build_context(cfg_path)
    return _CTX


def send_market_order(symbol: str, side: str, qty: float, ref_price: Optional[float] = None) -> None:
    if qty is None or qty <= 0:
        return
    ctx = _get_ctx()
    order = Order(
        order_id=f"{symbol}-{side}-{int(datetime.utcnow().timestamp()*1e6)}",
        symbol=symbol,
        side=side.lower(),
        qty=float(qty),
        price=float(ref_price) if ref_price is not None else None,
        type="market",
        ts=datetime.utcnow(),
    )
    # 标记最新价格以便成交价缺失时参考
    if ref_price is not None:
        ctx.portfolio.mark_price(symbol, float(ref_price))
    ctx.execution.send_order(order)


