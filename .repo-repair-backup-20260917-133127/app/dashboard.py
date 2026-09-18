from __future__ import annotations

import json
import math

import pandas as pd
import streamlit as st

from app.database import (
    get_trades,
    get_equity_history,
    get_open_theses,
    load_portfolio,
    load_initial_portfolio,
    DATA_DIR,
)

from app.premium_terminal import render_premium_terminal


st.set_page_config(
    page_title="EventPulse",
    page_icon="EP",
    layout="wide",
    initial_sidebar_state="expanded",
)

PIPELINE_FILE = DATA_DIR / ".eventpulse_pipeline.json"


def load_pipeline():
    if not PIPELINE_FILE.exists():
        return {}

    try:
        with PIPELINE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        number = float(value)

        if not math.isfinite(number):
            return default

        return number

    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


try:
    cash, positions = load_portfolio()
except Exception:
    cash = 0.0
    positions = {}


try:
    initial_positions = load_initial_portfolio()
except Exception:
    initial_positions = {}


portfolio = {
    "cash": safe_float(cash),
    "positions": positions or {},
}


pipeline = load_pipeline()


def load_equity_dataframe():
    try:
        rows = get_equity_history()
    except Exception:
        return pd.DataFrame(
            columns=[
                "id",
                "timestamp",
                "equity",
            ]
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "timestamp",
                "equity",
            ]
        )

    normalized = []

    for row in rows:
        try:
            if len(row) >= 4:
                row_id = row[0]
                timestamp = row[1]
                equity = row[3]

            elif len(row) == 3:
                row_id = row[0]
                timestamp = row[1]
                equity = row[2]

            else:
                continue

            normalized.append(
                {
                    "id": row_id,
                    "timestamp": timestamp,
                    "equity": safe_float(equity),
                }
            )

        except Exception:
            continue

    return pd.DataFrame(
        normalized,
        columns=[
            "id",
            "timestamp",
            "equity",
        ],
    )


equity_df = load_equity_dataframe()


if not equity_df.empty:
    current_equity = safe_float(
        equity_df.iloc[-1]["equity"]
    )
else:
    current_equity = 100000.0


equity_24h_ago = current_equity


if not equity_df.empty:
    try:
        history = equity_df.copy()

        history["timestamp"] = pd.to_datetime(
            history["timestamp"],
            errors="coerce",
        )

        history = history.dropna(
            subset=["timestamp"]
        )

        if not history.empty:
            cutoff = (
                pd.Timestamp.now()
                - pd.Timedelta(hours=24)
            )

            older = history[
                history["timestamp"] <= cutoff
            ]

            if not older.empty:
                equity_24h_ago = safe_float(
                    older.iloc[-1]["equity"],
                    current_equity,
                )

    except Exception:
        equity_24h_ago = current_equity


def load_latest_trades():
    try:
        rows = get_trades()
    except Exception:
        return pd.DataFrame()

    if not rows:
        return pd.DataFrame()

    columns = [
        "id",
        "timestamp",
        "ticker",
        "side",
        "quantity",
        "price",
        "value",
        "confidence",
        "reasoning",
    ]

    normalized = []

    for row in rows:
        try:
            values = list(row)

            if len(values) < len(columns):
                values.extend(
                    [None] * (
                        len(columns) - len(values)
                    )
                )

            values = values[:len(columns)]
            normalized.append(values)

        except Exception:
            continue

    if not normalized:
        return pd.DataFrame()

    return pd.DataFrame(
        normalized,
        columns=columns,
    )


trades_df = load_latest_trades()


def load_events():
    if trades_df.empty:
        return pd.DataFrame()

    df = trades_df.copy()

    if "ticker" in df.columns:
        df["ticker"] = (
            df["ticker"]
            .astype(str)
        )

    if "side" in df.columns:
        df["direction"] = (
            df["side"]
            .astype(str)
            .str.upper()
        )

    if "reasoning" in df.columns:
        df["headline"] = (
            df["reasoning"]
            .astype(str)
        )

    return df


events_df = load_events()


def thesis_dataframe():
    columns = [
        "id",
        "created_at",
        "ticker",
        "direction",
        "confidence",
        "thesis",
        "catalyst",
        "bull_case",
        "bear_case",
        "invalidation_condition",
        "expected_horizon",
        "entry_price",
        "current_price",
        "return_pct",
        "status",
        "resolved_at",
        "resolution_reason",
        "event_key",
    ]

    try:
        theses = get_open_theses()
    except Exception:
        return pd.DataFrame(columns=columns)

    if not theses:
        return pd.DataFrame(columns=columns)

    normalized = []

    for row in theses:
        try:
            values = list(row)

            if len(values) < len(columns):
                values.extend(
                    [None] * (
                        len(columns) - len(values)
                    )
                )

            values = values[:len(columns)]
            normalized.append(values)

        except Exception:
            continue

    if not normalized:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(
        normalized,
        columns=columns,
    )


theses_df = thesis_dataframe()


def position_quantity(position):
    if isinstance(position, dict):
        return safe_float(
            position.get(
                "quantity",
                0,
            )
        )

    return safe_float(position)


def position_price(position):
    if isinstance(position, dict):
        for key in (
            "average_price",
            "avg_price",
            "price",
            "entry_price",
        ):
            if key in position:
                return safe_float(
                    position.get(key)
                )

    return 0.0


def position_rows():
    rows = []

    for symbol, position in (
        positions or {}
    ).items():

        quantity = position_quantity(
            position
        )

        price = position_price(
            position
        )

        rows.append(
            {
                "ticker": str(symbol),
                "quantity": quantity,
                "average_price": price,
                "notional": quantity * price,
            }
        )

    return rows


position_data = position_rows()


def book_summary():
    if not position_data:
        return "CASH ONLY"

    chunks = []

    for row in position_data:
        quantity = row["quantity"]

        if quantity <= 0:
            continue

        chunks.append(
            f'{row["ticker"]} {quantity:g}'
        )

    if not chunks:
        return "CASH ONLY"

    return " · ".join(chunks[:5])


finalists = (
    pipeline.get(
        "finalists",
        [],
    )
    or []
)


def build_ticker_data():
    output = []

    for item in finalists:
        ticker = str(
            item.get(
                "execution_symbol",
                item.get(
                    "ticker",
                    "",
                ),
            )
        )

        if not ticker:
            continue

        price = safe_float(
            item.get(
                "last_price",
                0,
            )
        )

        change = safe_float(
            item.get(
                "change_24h_pct",
                0,
            )
        )

        turnover = safe_float(
            item.get(
                "turnover_24h",
                0,
            )
        )

        breakdown = item.get("evidence_breakdown") or {}

        output.append(
            {
                "symbol": ticker,
                "execution_symbol": ticker,
                "ticker": str(item.get("ticker", ticker)),
                "underlying": str(item.get("ticker", ticker)),
                "price": price,
                "last": price,
                "change_pct": change,
                "change_24h_pct": change,
                "quote_volume": turnover,
                "turnover_24h": turnover,
                "fast_score": safe_float(
                    item.get("fast_score", 0)
                ),
                "evidence_score": safe_float(
                    item.get("evidence_score", 0)
                ),
                "evidence_breakdown": {
                    str(key): safe_float(value)
                    for key, value in breakdown.items()
                },
            }
        )

    return output


ticker_data = build_ticker_data()


open_position_count = len(
    [
        row
        for row in position_data
        if row["quantity"] > 0
    ]
)


equity_change_pct = (
    (
        current_equity / 100000.0
    ) - 1.0
) * 100.0


pnl_24h = (
    current_equity
    - equity_24h_ago
)


risk_data = (
    pipeline.get(
        "risk",
        {},
    )
    or {}
)


execution_data = (
    pipeline.get(
        "paper_execution",
        {},
    )
    or {}
)


pipeline_for_ui = dict(pipeline)


pipeline_for_ui["risk"] = {
    "reviewed": safe_int(
        risk_data.get(
            "reviewed",
            0,
        )
    ),
    "approved": safe_int(
        risk_data.get(
            "approved",
            0,
        )
    ),
    "blocked": safe_int(
        risk_data.get(
            "blocked",
            0,
        )
    ),
}


pipeline_for_ui["paper_execution"] = {
    "attempted": safe_int(
        execution_data.get(
            "attempted",
            0,
        )
    ),
    "filled": safe_int(
        execution_data.get(
            "filled",
            0,
        )
    ),
    "failed": safe_int(
        execution_data.get(
            "failed",
            0,
        )
    ),
}


section = st.session_state.get("ep_page", "Overview")

render_premium_terminal(
    pipeline_snapshot=pipeline_for_ui,
    finalists=ticker_data,
    events=(
        events_df.to_dict("records")
        if not events_df.empty
        else []
    ),
    theses=(
        theses_df.to_dict("records")
        if not theses_df.empty
        else []
    ),
    equity=current_equity,
    equity_change=equity_change_pct,
    cash=safe_float(cash),
    positions=open_position_count,
    pnl_24h=pnl_24h,
    current_page=section,
)

st.markdown(
    '<div class="ep-footer">'
    'EVENTPULSE · EVENT-DRIVEN AUTONOMOUS TRADING TERMINAL '
    '· QWEN 3.8 MAX · BITGET REALITY · PAPER EXECUTION '
    '· DETERMINISTIC RISK'
    '</div>',
    unsafe_allow_html=True,
)
