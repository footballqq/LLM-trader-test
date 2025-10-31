from __future__ import annotations

from datetime import timedelta
from typing import Dict, Tuple, List

import numpy as np
import pandas as pd


def _periodize(df: pd.DataFrame, period: str) -> pd.Series:
    if period == "1D":
        return df["ts"].dt.floor("D")
    if period == "1W":
        return df["ts"].dt.to_period("W").dt.start_time
    if period == "1M":
        return df["ts"].dt.to_period("M").dt.start_time
    return df["ts"].dt.floor("D")


def compute_basic_trade_stats(trades: pd.DataFrame) -> Dict[str, float]:
    if trades.empty:
        return {"num_trades": 0, "win_rate": 0.0, "avg_payout": 0.0}
    # 需要有列：pnl
    if "pnl" not in trades.columns:
        return {"num_trades": len(trades), "win_rate": 0.0, "avg_payout": 0.0}
    wins = trades[trades["pnl"] > 0]
    loss = trades[trades["pnl"] <= 0]
    win_rate = len(wins) / max(len(trades), 1)
    avg_win = wins["pnl"].mean() if not wins.empty else 0.0
    avg_loss = -loss["pnl"].mean() if not loss.empty else 0.0
    payout = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    return {"num_trades": float(len(trades)), "win_rate": float(win_rate), "avg_payout": float(payout)}


def period_stats(equity_curve: pd.DataFrame, period: str = "1D") -> Dict[str, float]:
    if equity_curve.empty or "equity" not in equity_curve.columns:
        return {"return": 0.0, "max_dd": 0.0}
    eq = equity_curve.copy()
    eq["period"] = _periodize(eq.rename(columns={eq.columns[0]: "ts"}), period)
    grp = eq.groupby("period")["equity"].last()
    ret = grp.pct_change().fillna(0.0)
    cum = (1 + ret).cumprod()
    roll_max = cum.cummax()
    drawdown = (cum / roll_max - 1.0).fillna(0.0)
    return {"return": float(cum.iloc[-1] - 1.0), "max_dd": float(drawdown.min())}


def reconstruct_closed_trades_from_fills(fills_df: pd.DataFrame) -> pd.DataFrame:
    """
    依据成交明细（买正卖负）按 FIFO 配对生成闭合交易。
    需要列：ts(symbol datetime), symbol, qty(签名), price, commission。
    输出列：ts_open, ts_close, symbol, qty, entry_price, exit_price, pnl, hold_minutes。
    """
    required_cols = {"ts", "symbol", "qty", "price", "commission"}
    if fills_df is None or fills_df.empty or not required_cols.issubset(set(fills_df.columns)):
        return pd.DataFrame(columns=[
            "ts_open","ts_close","symbol","qty","entry_price","exit_price","pnl","hold_minutes"
        ])

    df = fills_df.copy().sort_values(["symbol", "ts"]).reset_index(drop=True)
    closed_rows: List[Dict[str, float]] = []
    inventories: Dict[str, List[Dict[str, float]]] = {}

    for _, row in df.iterrows():
        sym = str(row["symbol"])
        qty = float(row["qty"])  # 买入正，卖出负
        price = float(row["price"]) if row["price"] is not None else 0.0
        ts = pd.to_datetime(row["ts"]) if not pd.isna(row["ts"]) else pd.NaT
        commission = float(row["commission"]) if row["commission"] is not None else 0.0

        if sym not in inventories:
            inventories[sym] = []

        # 入库（正方向）
        if qty > 0:
            inventories[sym].append({"qty": qty, "price": price, "ts": ts, "commission": commission})
            continue

        # 卖出/平仓：与库存 FIFO 配对
        remaining = -qty  # 需要平掉的正数量
        while remaining > 0 and inventories[sym]:
            lot = inventories[sym][0]
            take = min(remaining, lot["qty"])  # 成交配对数量
            # 分摊佣金：按数量比例
            entry_comm_part = (take / lot["qty"]) * float(lot.get("commission", 0.0)) if lot["qty"] > 0 else 0.0
            exit_comm_part = (take / (-qty)) * commission if (-qty) > 0 else 0.0

            pnl = (price - lot["price"]) * take - entry_comm_part - exit_comm_part
            hold_minutes = None
            try:
                delta = (ts - lot["ts"]).total_seconds() / 60.0
                hold_minutes = float(delta)
            except Exception:
                hold_minutes = None

            closed_rows.append({
                "ts_open": lot["ts"],
                "ts_close": ts,
                "symbol": sym,
                "qty": take,
                "entry_price": lot["price"],
                "exit_price": price,
                "pnl": pnl,
                "hold_minutes": hold_minutes if hold_minutes is not None else 0.0,
            })

            lot["qty"] -= take
            remaining -= take
            if lot["qty"] <= 1e-12:
                inventories[sym].pop(0)

        # 若卖出数量超过库存，视为反向开仓的超出部分，加入库存（做空）。
        if remaining > 1e-12:
            # 将未匹配部分作为“负库存”（做空），为简单起见，记录为单独方向库存，以负量标识。
            inventories[sym].insert(0, {"qty": -remaining, "price": price, "ts": ts, "commission": commission})

    if not closed_rows:
        return pd.DataFrame(columns=[
            "ts_open","ts_close","symbol","qty","entry_price","exit_price","pnl","hold_minutes"
        ])
    out = pd.DataFrame(closed_rows)
    out["ts_open"] = pd.to_datetime(out["ts_open"])  # type: ignore
    out["ts_close"] = pd.to_datetime(out["ts_close"])  # type: ignore
    return out.sort_values("ts_close").reset_index(drop=True)



