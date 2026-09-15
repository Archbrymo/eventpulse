from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import math

import pandas as pd
import streamlit as st

from app.news import get_market_events
from app.market import get_market_data

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



# -----------------------------
# EVENTPULSE V2 TERMINAL
# -----------------------------

st.markdown("""
<style>
.ep-v2 { color:#D8DEE9; }
.ep-v2 .muted { color:#7F8998; font-size:12px; }
.ep-v2 .label { color:#7F8998; font-size:11px; letter-spacing:.08em; }
.ep-v2 .value { color:#F2F5F7; font-size:24px; font-weight:700; }
.ep-v2 .panel {
    background:#12151A;
    border:1px solid #242932;
    border-radius:4px;
    padding:16px;
    margin-bottom:14px;
}
.ep-v2 .teal { color:#2EE6C8; }
.ep-v2 .green { color:#3DDC97; }
.ep-v2 .red { color:#E23B3B; }
.ep-v2 .news {
    border-bottom:1px solid #242932;
    padding:11px 0;
}
.ep-v2 .ticker {
    background:#12151A;
    border:1px solid #242932;
    padding:8px 10px;
    min-height:58px;
}
</style>
<div class="ep-v2">
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## EVENTPULSE")
    st.caption("AUTONOMOUS EVENT-DRIVEN TRADING")

    pages = [
        "Overview",
        "Portfolio",
        "Events",
        "Qwen Council",
        "Risk",
        "Execution",
        "Thesis",
    ]

    current_page = st.session_state.get("ep_page", "Overview")

    for page in pages:
        if st.button(
            page,
            key=f"v2_nav_{page}",
            use_container_width=True,
            type="primary" if current_page == page else "secondary",
        ):
            st.session_state.ep_page = page
            st.rerun()

    st.divider()

    st.caption("SYSTEM")
    st.success("US CASH CLOSED")
    st.success("rTOKEN LIVE")
    st.info("PAPER")

    st.button(
        "KILL ARMED",
        key="v2_kill",
        use_container_width=True,
        type="secondary",
    )

    st.divider()

    st.caption("AGENT SEARCH")
    search_query = st.text_input(
        "Search",
        placeholder="ticker / event / thesis...",
        label_visibility="collapsed",
        key="v2_agent_search",
    )

    st.caption("TEST ACCOUNT")
    st.metric("Starting equity", "$100,000")
    st.button(
        "RESET TEST ACCOUNT",
        key="v2_reset",
        use_container_width=True,
        disabled=True,
        help="Reset action will be enabled after the database reset path is verified.",
    )

# Search result resolution
def search_items(query):
    if not query:
        return []

    q = query.strip().lower()
    matches = []

    for row in ticker_data:
        text = " ".join(
            str(row.get(k, ""))
            for k in ("ticker", "symbol", "underlying")
        ).lower()
        if q in text:
            matches.append(
                ("ASSET", row.get("symbol", row.get("ticker", "")))
            )

    for row in events_df.to_dict("records") if not events_df.empty else []:
        text = " ".join(str(v) for v in row.values()).lower()
        if q in text:
            matches.append(
                ("EVENT", row.get("ticker", "EVENT"))
            )

    for row in theses_df.to_dict("records") if not theses_df.empty else []:
        text = " ".join(str(v) for v in row.values()).lower()
        if q in text:
            matches.append(
                ("THESIS", row.get("ticker", "THESIS"))
            )

    return matches[:8]


search_results = search_items(search_query)

if search_results:
    st.sidebar.markdown("**SEARCH RESULTS**")
    for kind, value in search_results:
        st.sidebar.write(f"{kind} · {value}")

# Selected ticker
available_tickers = [
    str(x.get("symbol") or x.get("ticker"))
    for x in ticker_data
    if x.get("symbol") or x.get("ticker")
]

available_tickers = list(dict.fromkeys(available_tickers))

if not available_tickers:
    available_tickers = ["No asset data"]

selected_asset = st.session_state.get(
    "v2_selected_asset",
    available_tickers[0],
)

if selected_asset not in available_tickers:
    selected_asset = available_tickers[0]

# Search can select an asset automatically
if search_results:
    candidate = search_results[0][1]
    if candidate in available_tickers:
        selected_asset = candidate
        st.session_state.v2_selected_asset = candidate

st.session_state.v2_selected_asset = selected_asset

# Header
st.markdown(
    '<div class="label">EVENTPULSE · AUTONOMOUS EVENT-DRIVEN TRADING</div>',
    unsafe_allow_html=True,
)

h1, h2 = st.columns([3, 1])
with h1:
    st.title("Trading Overview")
with h2:
    st.caption("LAST TICK")
    st.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.caption("PAPER · US CASH CLOSED")

# Exactly four KPIs
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric("EQUITY", f"${current_equity:,.2f}", f"{equity_change_pct:+.2f}%")

with k2:
    st.metric("24H PNL", f"${pnl_24h:,.2f}")

with k3:
    st.metric("CASH", f"${safe_float(cash):,.2f}")

with k4:
    st.metric("POSITIONS", str(open_position_count))

# Pipeline
st.markdown("### AUTONOMOUS PIPELINE")

pipeline_counts = [
    ("REALITY", pipeline.get("reality", 1173)),
    ("FAST", pipeline.get("fast", 50)),
    ("EVIDENCE", pipeline.get("evidence", 10)),
    ("QWEN", pipeline.get("qwen", 3)),
    ("RISK", risk_data.get("reviewed", 0)),
    ("APPROVED", risk_data.get("approved", 0)),
    ("FILLED", execution_data.get("filled", 0)),
]

pipe_cols = st.columns(len(pipeline_counts))

for col, (label, value) in zip(pipe_cols, pipeline_counts):
    with col:
        st.markdown(
            f'<div class="panel"><div class="label">{label}</div>'
            f'<div class="value">{safe_int(value):,}</div></div>',
            unsafe_allow_html=True,
        )

st.caption("1173 reality instruments → 50 fast candidates → 10 evidence finalists")

# Top 15 CEX-style moving ticker tape
st.markdown("### TOP REALITY TICKERS")

top_tickers = ticker_data[:15]

if top_tickers:
    cards = []

    for row in top_tickers:
        symbol = str(row.get("symbol", row.get("ticker", "")))
        price = safe_float(row.get("price"))
        move = safe_float(row.get("change_24h_pct"))
        score = safe_float(row.get("evidence_score"))

        move_class = "up" if move >= 0 else "down"
        move_sign = "+" if move >= 0 else ""

        cards.append(
            f"""
            <div class="ep-tape-item">
                <div class="ep-tape-symbol">{symbol}</div>
                <div class="ep-tape-price">${price:,.2f}</div>
                <div class="ep-tape-move {move_class}">
                    {move_sign}{move:.2f}%
                </div>
                <div class="ep-tape-score">E {score:.0f}</div>
            </div>
            """
        )

    tape = "".join(cards)

    st.markdown(
        f"""
        <style>
        .ep-tape-window {{
            width:100%;
            overflow:hidden;
            background:#0B0D10;
            border-top:1px solid #242932;
            border-bottom:1px solid #242932;
            padding:0;
            position:relative;
        }}

        .ep-tape-track {{
            display:flex;
            width:max-content;
            animation:epTickerMove 42s linear infinite;
            will-change:transform;
        }}

        .ep-tape-window:hover .ep-tape-track {{
            animation-play-state:paused;
        }}

        .ep-tape-item {{
            display:grid;
            grid-template-columns:auto auto auto auto;
            align-items:center;
            gap:12px;
            min-width:245px;
            padding:13px 18px;
            border-right:1px solid #242932;
            font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
            white-space:nowrap;
        }}

        .ep-tape-symbol {{
            color:#F2F5F7;
            font-weight:700;
            letter-spacing:.03em;
        }}

        .ep-tape-price {{
            color:#AAB2BF;
        }}

        .ep-tape-move {{
            font-weight:700;
        }}

        .ep-tape-move.up {{
            color:#3DDC97;
        }}

        .ep-tape-move.down {{
            color:#E23B3B;
        }}

        .ep-tape-score {{
            color:#2EE6C8;
            font-size:11px;
        }}

        @keyframes epTickerMove {{
            from {{
                transform:translateX(0);
            }}
            to {{
                transform:translateX(-50%);
            }}
        }}
        </style>

        <div class="ep-tape-window">
            <div class="ep-tape-track">
                {tape}
                {tape}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("Hover to pause · Select an asset below to drive Live Evidence")

    selected_from_tape = st.selectbox(
        "ACTIVE REALITY ASSET",
        available_tickers,
        index=available_tickers.index(selected_asset)
        if selected_asset in available_tickers else 0,
        label_visibility="collapsed",
        key="v2_active_asset",
    )

    if selected_from_tape != st.session_state.get("v2_selected_asset"):
        st.session_state.v2_selected_asset = selected_from_tape
        st.rerun()

else:
    st.info("Reality universe data is not available in the latest pipeline snapshot.")

# Selected asset
selected_row = next(
    (
        row for row in ticker_data
        if str(row.get("symbol")) == selected_asset
    ),
    {},
)

selected_ticker = str(
    selected_row.get(
        "ticker",
        selected_asset,
    )
)

selected_price = safe_float(
    selected_row.get("price")
)

selected_move = safe_float(
    selected_row.get("change_24h_pct")
)

# Main content
left, right = st.columns([1.65, 1])

with left:
    st.markdown("### MARKET / NEWS")

    try:
        news_tickers = [
            str(x.get("ticker"))
            for x in ticker_data[:15]
            if x.get("ticker")
        ]
        live_events = get_market_events(
            tickers=news_tickers
        )
    except Exception:
        live_events = []

    if live_events:
        for i, event in enumerate(live_events[:8]):
            ticker = str(event.get("ticker", "—"))
            headline = str(event.get("headline", "No headline"))
            catalyst = str(event.get("catalyst", "mixed"))
            relevance = safe_float(event.get("relevance"))

            news_col, action_col = st.columns([5, 1])

            with news_col:
                st.markdown(
                    f"""
                    <div class="news">
                        <b>{ticker}</b>
                        <span class="muted"> · relevance {relevance:.2f}</span><br>
                        {headline}<br>
                        <span class="teal">{catalyst.upper()}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with action_col:
                if st.button(
                    "OPEN",
                    key=f"news_open_{i}_{ticker}",
                    use_container_width=True,
                ):
                    matching = next(
                        (
                            row for row in ticker_data
                            if str(row.get("ticker", "")).upper()
                            == ticker.upper()
                            or str(row.get("symbol", "")).upper()
                            == ticker.upper()
                        ),
                        None,
                    )

                    if matching:
                        st.session_state.v2_selected_asset = str(
                            matching.get("symbol", matching.get("ticker"))
                        )
                        st.rerun()
    else:
        st.info("No actionable market events returned by the latest evidence scan.")

    st.markdown("### BULL CASE / BEAR CASE")

    thesis_matches = (
        theses_df[
            theses_df["ticker"].astype(str).str.upper()
            == selected_ticker.upper()
        ]
        if not theses_df.empty
        else pd.DataFrame()
    )

    if not thesis_matches.empty:
        thesis = thesis_matches.iloc[0]

        bull = str(
            thesis.get(
                "bull_case",
                "",
            )
            or "No bull case recorded yet."
        )

        bear = str(
            thesis.get(
                "bear_case",
                "",
            )
            or "No bear case recorded yet."
        )

        invalidation = str(
            thesis.get(
                "invalidation_condition",
                "",
            )
            or "No invalidation condition recorded."
        )
    else:
        bull = (
            f"{selected_ticker} has a "
            f"{selected_move:+.2f}% 24h move with evidence score "
            f"{safe_float(selected_row.get('evidence_score')):.0f}. "
            "Further catalyst confirmation is required."
        )

        bear = (
            "Momentum can reverse if the underlying event thesis weakens, "
            "market quality deteriorates, or evidence becomes contradictory."
        )

        invalidation = (
            "Evidence balance deteriorates or the event catalyst is invalidated."
        )

    b1, b2 = st.columns(2)

    with b1:
        st.success("BULL")
        st.write(bull)

    with b2:
        st.error("BEAR")
        st.write(bear)

    st.caption(f"INVALIDATION · {invalidation}")

    st.markdown("### QWEN DECISION → RISK → PAPER EXECUTION")

    qwen_items = pipeline.get("qwen_decisions") or pipeline.get("qwen") or []

    if isinstance(qwen_items, list) and qwen_items:
        for decision in qwen_items[:3]:
            st.write(
                f"**{decision.get('ticker', '—')}** · "
                f"{decision.get('decision', 'WAIT')} · "
                f"confidence {safe_float(decision.get('confidence')):.2f}"
            )
    else:
        st.info(
            "Qwen council output will appear here when the latest agent cycle "
            "writes its decision snapshot."
        )

with right:
    st.markdown("### LIVE EVIDENCE")

    st.markdown(
        f'<div class="panel"><div class="label">SELECTED ASSET</div>'
        f'<div class="value teal">{selected_asset}</div>'
        f'<div class="muted">{selected_ticker}</div></div>',
        unsafe_allow_html=True,
    )

    st.metric(
        "PRICE",
        f"${selected_price:,.2f}",
        f"{selected_move:+.2f}%",
    )

    st.markdown("#### EVIDENCE SCORE")

    evidence_score = safe_float(
        selected_row.get("evidence_score")
    )

    st.progress(
        min(max(evidence_score / 100.0, 0.0), 1.0)
    )

    breakdown = selected_row.get(
        "evidence_breakdown",
        {},
    ) or {}

    if breakdown:
        evidence_df = pd.DataFrame(
            [
                {
                    "Evidence": str(k).replace("_", " ").title(),
                    "Score": safe_float(v),
                }
                for k, v in breakdown.items()
            ]
        )

        st.dataframe(
            evidence_df,
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### MARKET DATA")

    st.write(
        f"Turnover: **${safe_float(selected_row.get('turnover_24h')):,.2f}**"
    )

    st.write(
        f"Fast score: **{safe_float(selected_row.get('fast_score')):.1f}**"
    )

    st.write(
        f"Evidence score: **{evidence_score:.1f}**"
    )

    # Real supplementary price history
    try:
        market = get_market_data(selected_ticker)

        if isinstance(market, dict):
            history = market.get("history") or market.get("prices") or []

            if history:
                st.line_chart(pd.Series(history))
    except Exception:
        pass

    if st.button(
        "OPEN THESIS",
        key="v2_open_thesis",
        use_container_width=True,
    ):
        st.session_state.ep_page = "Thesis"
        st.rerun()

# Bottom agent search / reasoning
st.markdown("### AGENT SEARCH")

agent_query = st.text_input(
    "Search the agent's knowledge trail",
    placeholder="Search ticker, event, thesis, trade reasoning...",
    key="v2_bottom_agent_search",
)

if agent_query:
    results = search_items(agent_query)

    if results:
        for kind, value in results:
            st.write(f"**{kind}** · {value}")
    else:
        st.info("No matching evidence, event, thesis, or trade reasoning found.")

st.markdown(
    "</div>"
    '<div class="ep-footer">'
    "EVENTPULSE · EVENT-DRIVEN AUTONOMOUS TRADING TERMINAL · "
    "QWEN 3.8 MAX · BITGET REALITY · PAPER EXECUTION · DETERMINISTIC RISK"
    "</div>",
    unsafe_allow_html=True,
)

