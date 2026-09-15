from __future__ import annotations

from pathlib import Path
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
)

from app.ui_terminal import terminal_css

from app.premium_terminal import render_premium_terminal


st.set_page_config(
    page_title="EventPulse",
    page_icon="EP",
    layout="wide",
    initial_sidebar_state="expanded",
)

terminal_css()

BASE_DIR = Path(__file__).resolve().parent.parent
PIPELINE_FILE = BASE_DIR / ".eventpulse_pipeline.json"


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

        output.append(
            {
                "symbol": ticker,
                "price": price,
                "last": price,
                "change_pct": change,
                "change_24h_pct": change,
                "quote_volume": turnover,
                "turnover_24h": turnover,
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


section = st.sidebar.radio(
    "NAVIGATION",
    [
        "Overview",
        "Portfolio",
        "Events",
        "Qwen Council",
        "Risk",
        "Execution",
        "Thesis",
        "Agent Search",
    ],
)


if section == "Overview":

    render_premium_terminal(
        pipeline=pipeline_for_ui,
        ticker_data=ticker_data,
        events=(
            events_df.to_dict("records")
            if not events_df.empty
            else []
        ),
        equity=current_equity,
        equity_change=equity_change_pct,
        cash=safe_float(cash),
        positions=open_position_count,
        pnl_24h=pnl_24h,
        active="Overview",
    )


elif section == "Portfolio":

    st.subheader("PORTFOLIO")

    st.caption(
        "PAPER ACCOUNT · READ ONLY"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "EQUITY",
            f"${current_equity:,.2f}",
        )

    with c2:
        st.metric(
            "CASH",
            f"${safe_float(cash):,.2f}",
        )

    with c3:
        st.metric(
            "OPEN POSITIONS",
            open_position_count,
        )

    if position_data:

        portfolio_df = pd.DataFrame(
            position_data
        )

        portfolio_df = (
            portfolio_df[
                portfolio_df["quantity"] > 0
            ]
            .copy()
        )

        st.dataframe(
            portfolio_df,
            width="stretch",
            hide_index=True,
        )

    else:

        st.info(
            "No open positions."
        )


elif section == "Events":

    render_premium_terminal(
        pipeline=pipeline_for_ui,
        ticker_data=ticker_data,
        events=(
            events_df.to_dict("records")
            if not events_df.empty
            else []
        ),
        equity=current_equity,
        equity_change=equity_change_pct,
        cash=safe_float(cash),
        positions=open_position_count,
        pnl_24h=pnl_24h,
        active="Events",
    )


elif section == "Qwen Council":

    st.subheader("QWEN COUNCIL")

    qwen_count = safe_int(
        pipeline.get(
            "qwen_council",
            0,
        )
    )

    signal_count = safe_int(
        pipeline.get(
            "qwen_signals",
            0,
        )
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "COUNCIL CANDIDATES",
            qwen_count,
        )

    with c2:
        st.metric(
            "SIGNALS",
            signal_count,
        )

    with c3:
        st.metric(
            "MODEL",
            "QWEN 3.8 MAX",
        )

    st.markdown(
        '<div class="ep-panel">'
        '<div class="ep-panel-head">'
        'QWEN INVESTMENT COUNCIL'
        '</div>'
        '<div class="ep-panel-body">'
        'Qwen receives the evidence pack assembled by '
        'EventPulse and produces BUY / SELL / HOLD / WAIT '
        'decisions.'
        '<br><br>'
        'The model does not directly execute orders. '
        'Deterministic risk controls remain authoritative.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if finalists:

        council_rows = []

        for item in finalists:

            council_rows.append(
                {
                    "ticker": item.get(
                        "ticker",
                        item.get(
                            "underlying",
                            "",
                        ),
                    ),
                    "evidence_score": item.get(
                        "evidence_score",
                        0,
                    ),
                    "market_change": item.get(
                        "change_24h_pct",
                        0,
                    ),
                    "last_price": item.get(
                        "last_price",
                        0,
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(council_rows),
            width="stretch",
            hide_index=True,
        )


elif section == "Risk":

    st.subheader("RISK CONTROL")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "REVIEWED",
            safe_int(
                risk_data.get(
                    "reviewed",
                    0,
                )
            ),
        )

    with c2:
        st.metric(
            "APPROVED",
            safe_int(
                risk_data.get(
                    "approved",
                    0,
                )
            ),
        )

    with c3:
        st.metric(
            "BLOCKED",
            safe_int(
                risk_data.get(
                    "blocked",
                    0,
                )
            ),
        )

    st.markdown(
        '<div class="ep-panel">'
        '<div class="ep-panel-head">'
        'DETERMINISTIC RISK LIMITS'
        '</div>'
        '<div class="ep-panel-body">'
        '<b>MIN CONFIDENCE</b> &nbsp; 60%'
        '<br><br>'
        '<b>MAX TRADE</b> &nbsp; 10% of portfolio'
        '<br><br>'
        '<b>MAX POSITION</b> &nbsp; 20% of portfolio'
        '<br><br>'
        '<b>MAX DAILY LOSS</b> &nbsp; 2%'
        '<br><br>'
        '<b>MAX DRAWDOWN</b> &nbsp; 10%'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


elif section == "Execution":

    st.subheader("EXECUTION")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "ORDERS ATTEMPTED",
            safe_int(
                execution_data.get(
                    "attempted",
                    0,
                )
            ),
        )

    with c2:
        st.metric(
            "FILLED",
            safe_int(
                execution_data.get(
                    "filled",
                    0,
                )
            ),
        )

    with c3:
        st.metric(
            "FAILED",
            safe_int(
                execution_data.get(
                    "failed",
                    0,
                )
            ),
        )

    if trades_df.empty:

        st.info(
            "No paper execution receipts yet."
        )

    else:

        st.dataframe(
            trades_df.tail(25),
            width="stretch",
            hide_index=True,
        )


elif section == "Thesis":

    st.subheader("THESIS TRACKING")

    if theses_df.empty:

        st.info(
            "No open theses."
        )

    else:

        status_counts = (
            theses_df["status"]
            .fillna("UNKNOWN")
            .value_counts()
            .to_dict()
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "OPEN",
                safe_int(
                    status_counts.get(
                        "OPEN",
                        0,
                    )
                ),
            )

        with c2:
            st.metric(
                "VALIDATED",
                safe_int(
                    status_counts.get(
                        "VALIDATED",
                        0,
                    )
                ),
            )

        with c3:
            st.metric(
                "UNRESOLVED",
                safe_int(
                    status_counts.get(
                        "UNRESOLVED",
                        0,
                    )
                ),
            )

        display_columns = [
            column
            for column in [
                "id",
                "created_at",
                "ticker",
                "direction",
                "confidence",
                "thesis",
                "expected_horizon",
                "entry_price",
                "current_price",
                "return_pct",
                "status",
            ]
            if column in theses_df.columns
        ]

        st.dataframe(
            theses_df[display_columns],
            width="stretch",
            hide_index=True,
        )

        st.markdown(
            '<div class="ep-panel">'
            '<div class="ep-panel-head">'
            'THESIS ENGINE'
            '</div>'
            '<div class="ep-panel-body">'
            'Thesis state is evaluated separately from trade '
            'execution.'
            '<br><br>'
            'A thesis may remain OPEN, become VALIDATED, or '
            'remain UNRESOLVED when evidence is insufficient.'
            '<br><br>'
            'Strong contradiction can invalidate a thesis '
            'before its maximum horizon.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )


elif section == "Agent Search":

    st.subheader("AGENT SEARCH")

    universe = safe_int(
        pipeline.get(
            "reality_universe",
            0,
        )
    )

    screened = safe_int(
        pipeline.get(
            "fast_screen",
            0,
        )
    )

    researched = safe_int(
        pipeline.get(
            "evidence_research",
            0,
        )
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "REALITY ASSETS",
            universe,
        )

    with c2:
        st.metric(
            "FAST SCREEN",
            screened,
        )

    with c3:
        st.metric(
            "EVIDENCE RESEARCH",
            researched,
        )

    st.markdown(
        '<div class="ep-panel">'
        '<div class="ep-panel-head">'
        'REALITY UNIVERSE'
        '</div>'
        '<div class="ep-panel-body">'
        'EventPulse searches the live Bitget Reality '
        'tokenized-stock universe, screens candidates, '
        'enriches them with evidence, and passes the final '
        'research pack to Qwen.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if finalists:

        rows = []

        for item in finalists:

            rows.append(
                {
                    "ticker": item.get(
                        "ticker",
                        item.get(
                            "underlying",
                            "",
                        ),
                    ),
                    "execution_symbol": item.get(
                        "execution_symbol",
                        "",
                    ),
                    "fast_score": item.get(
                        "fast_score",
                        item.get(
                            "score",
                            0,
                        ),
                    ),
                    "evidence_score": item.get(
                        "evidence_score",
                        0,
                    ),
                    "last_price": item.get(
                        "last_price",
                        0,
                    ),
                    "change_24h_pct": item.get(
                        "change_24h_pct",
                        0,
                    ),
                    "turnover_24h": item.get(
                        "turnover_24h",
                        0,
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            width="stretch",
            hide_index=True,
        )

    else:

        st.info(
            "No research finalists in the latest pipeline snapshot."
        )


st.markdown(
    '<div class="ep-footer">'
    'EVENTPULSE · EVENT-DRIVEN AUTONOMOUS TRADING TERMINAL '
    '· QWEN 3.8 MAX · BITGET REALITY · PAPER EXECUTION '
    '· DETERMINISTIC RISK'
    '</div>',
    unsafe_allow_html=True,
)