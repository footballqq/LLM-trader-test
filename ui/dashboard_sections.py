from __future__ import annotations

from typing import Dict, List

import pandas as pd
import streamlit as st

from ..portfolio.portfolio_state import PortfolioState
from ..portfolio.metrics import period_stats, compute_basic_trade_stats, reconstruct_closed_trades_from_fills


def section_market(symbol: str, ohlcv: pd.DataFrame) -> None:
    st.subheader(f"行情 - {symbol}")
    if ohlcv.empty:
        st.info("无数据")
        return
    st.line_chart(ohlcv.set_index("datetime")["close"], height=200)


def section_positions(portfolio: PortfolioState) -> None:
    st.subheader("持仓与资金")
    pos_df = (
        pd.DataFrame([{"symbol": s, "qty": q, "last_price": portfolio.last_price.get(s)} for s, q in portfolio.positions.items()])
        if portfolio.positions
        else pd.DataFrame(columns=["symbol", "qty", "last_price"])
    )
    st.dataframe(pos_df, use_container_width=True)
    st.metric("现金", f"{portfolio.cash:,.2f}")
    st.metric("权益", f"{portfolio.equity():,.2f}")


def section_trades(portfolio: PortfolioState) -> None:
    st.subheader("成交记录")
    trades = portfolio.to_dataframe()
    st.dataframe(trades, use_container_width=True)


def section_stats_from_state(state_df: pd.DataFrame) -> None:
    st.subheader("统计 - 多周期收益与回撤")
    if state_df.empty or "total_equity" not in state_df.columns:
        st.info("无组合权益数据")
        return
    eq_df = state_df.reset_index()[["timestamp", "total_equity"]].rename(columns={"timestamp": "ts", "total_equity": "equity"})
    stats_1d = period_stats(eq_df.copy(), period="1D")
    stats_1w = period_stats(eq_df.copy(), period="1W")
    stats_1m = period_stats(eq_df.copy(), period="1M")

    col1, col2, col3 = st.columns(3)
    col1.metric("1D 回报", f"{stats_1d['return']*100:.2f}%")
    col1.metric("1D 最大回撤", f"{stats_1d['max_dd']*100:.2f}%")
    col2.metric("1W 回报", f"{stats_1w['return']*100:.2f}%")
    col2.metric("1W 最大回撤", f"{stats_1w['max_dd']*100:.2f}%")
    col3.metric("1M 回报", f"{stats_1m['return']*100:.2f}%")
    col3.metric("1M 最大回撤", f"{stats_1m['max_dd']*100:.2f}%")


def section_trade_stats(trades_df: pd.DataFrame, portfolio: PortfolioState | None = None) -> None:
    st.subheader("交易统计 - 胜率与赔率")
    df: pd.DataFrame
    # 优先使用 CSV 的 trade_history；否则尝试从 PortfolioState.fills 重建闭合交易
    if trades_df is not None and not trades_df.empty and "pnl" in trades_df.columns:
        df = trades_df.copy()
        df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce")
        df = df.dropna(subset=["pnl"])  # 使用记录里的净盈亏
    elif portfolio is not None:
        fills = portfolio.to_dataframe()
        if not fills.empty:
            closed = reconstruct_closed_trades_from_fills(
                fills.rename(columns={"ts": "ts", "price": "price", "qty": "qty", "commission": "commission"})
            )
            df = closed
        else:
            st.info("无成交数据")
            return
    else:
        st.info("无成交数据")
        return
    stats = compute_basic_trade_stats(df)
    col1, col2, col3 = st.columns(3)
    col1.metric("笔数", f"{int(stats['num_trades'])}")
    col2.metric("胜率", f"{stats['win_rate']*100:.2f}%")
    col3.metric("赔率", f"{stats['avg_payout']:.2f} : 1")


