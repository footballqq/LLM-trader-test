#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random

import numpy as np
import pandas as pd


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def gen_equity_series(n: int = 240, start_equity: float = 1_000_000.0) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    times = [now - timedelta(minutes=n - i) for i in range(n)]
    rets = np.random.normal(loc=0.0002, scale=0.003, size=n)  # 小幅波动
    equity = [start_equity]
    for r in rets[1:]:
        equity.append(equity[-1] * (1 + float(r)))
    df = pd.DataFrame({
        "timestamp": [t.isoformat() for t in times],
        "total_balance": np.round(np.array(equity) * 0.99, 2),
        "total_equity": np.round(equity, 2),
        "total_return_pct": np.round((np.array(equity) / start_equity - 1) * 100, 2),
        "num_positions": np.random.randint(0, 4, size=n),
        "position_details": ["No positions"] * n,
        "total_margin": np.round(np.random.uniform(0, 50_000, size=n), 2),
        "net_unrealized_pnl": np.round(np.random.uniform(-5_000, 5_000, size=n), 2),
    })
    return df


def gen_trades(m: int = 20) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    rows = []
    coins = ["BTC", "ETH", "IF", "IC"]
    for i in range(m):
        ts = now - timedelta(minutes=random.randint(10, 600))
        qty = round(random.uniform(0.01, 1.5), 4)
        price = round(random.uniform(100, 60000), 2)
        pnl = round(random.uniform(-200, 300), 2)
        rows.append({
            "timestamp": ts.isoformat(),
            "coin": random.choice(coins),
            "action": random.choice(["ENTRY", "CLOSE"]),
            "side": random.choice(["long", "short"]),
            "quantity": qty,
            "price": price,
            "profit_target": round(price * 1.02, 2),
            "stop_loss": round(price * 0.98, 2),
            "leverage": random.choice([1, 2, 5, 10]),
            "confidence": round(random.uniform(0.3, 0.9), 2),
            "pnl": pnl,
            "balance_after": round(1_000_000 + pnl, 2),
            "reason": "mock"
        })
    df = pd.DataFrame(rows).sort_values("timestamp")
    return df


def gen_ai_decisions(k: int = 20) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(k):
        ts = now - timedelta(minutes=i * 5)
        rows.append({
            "timestamp": ts.isoformat(),
            "coin": random.choice(["BTC", "ETH", "IF", "IC"]),
            "signal": random.choice(["entry", "hold", "close"]),
            "reasoning": "mock reasoning",
            "confidence": round(random.uniform(0.4, 0.9), 2),
        })
    return pd.DataFrame(rows).sort_values("timestamp")


def gen_ai_messages(k: int = 30) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(k):
        ts = now - timedelta(minutes=i * 3)
        rows.append({
            "timestamp": ts.isoformat(),
            "direction": random.choice(["sent", "received"]),
            "role": random.choice(["system", "user", "assistant"]),
            "content": f"BTC MARKET SNAPSHOT - Price: {round(random.uniform(20000, 70000), 2)}",
            "metadata": "",
        })
    return pd.DataFrame(rows).sort_values("timestamp")


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = Path(os.getenv("TRADEBOT_DATA_DIR", str(base_dir / "data")))
    ensure_dir(data_dir)

    # Generate
    state_df = gen_equity_series(n=240)
    trades_df = gen_trades(m=30)
    decisions_df = gen_ai_decisions(k=40)
    messages_df = gen_ai_messages(k=60)

    # Write CSVs compatible with dashboard
    state_df.to_csv(data_dir / "portfolio_state.csv", index=False, encoding="utf-8")
    trades_df.to_csv(data_dir / "trade_history.csv", index=False, encoding="utf-8")
    decisions_df.to_csv(data_dir / "ai_decisions.csv", index=False, encoding="utf-8")
    messages_df.to_csv(data_dir / "ai_messages.csv", index=False, encoding="utf-8")

    print(f"Mock data written to: {data_dir}")


if __name__ == "__main__":
    main()


