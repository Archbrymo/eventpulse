from pathlib import Path
import json
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from app.database import (
    get_connection,
    get_events,
    get_equity_history,
    get_open_theses,
    get_trades,
    load_initial_portfolio,
    load_portfolio,
)

st.set_page_config(
    page_title="EventPulse",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIG
# ============================================================

INITIAL_EQUITY = 100_000.00
PIPELINE_FILE = Path(".eventpulse_pipeline.json")


# ============================================================
# GLOBAL CSS
# ============================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --bg: #070B14;
        --bg2: #0A101B;
        --panel: #0A111D;
        --panel2: #0C1420;
        --line: #1E2A3A;
        --line2: #172131;
        --text: #E5E7EB;
        --muted: #64748B;
        --muted2: #94A3B8;
        --blue: #7DD3FC;
        --blue2: #38BDF8;
        --green: #4ADE80;
        --red: #F87171;
        --yellow: #FACC15;
    }

    * {
        box-sizing: border-box;
    }

    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"] {
        background: var(--bg) !important;
        color: var(--text) !important;
    }

    .stApp {
        background:
            linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px),
            radial-gradient(
                circle at 70% 0%,
                rgba(56,189,248,0.07),
                transparent 34%
            ),
            var(--bg) !important;

        background-size:
            32px 32px,
            32px 32px,
            auto,
            auto;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    [data-testid="stToolbar"] {
        display: none !important;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    .block-container {
        max-width: 1600px;
        padding-top: 1rem;
        padding-bottom: 3rem;
    }

    h1,
    h2,
    h3 {
        color: var(--blue) !important;
        font-family: "Inter", sans-serif !important;
        letter-spacing: -0.02em;
    }

    p,
    span,
    div,
    label {
        font-family: "Inter", sans-serif;
    }

    code,
    pre,
    .mono {
        font-family: "IBM Plex Mono", monospace !important;
    }

    /* ========================================================
       SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {
        background: #060A12 !important;
        border-right: 1px solid var(--line) !important;
    }

    section[data-testid="stSidebar"] > div {
        padding: 18px 12px 20px 12px !important;
    }

    .ep-sidebar-brand {
        color: var(--blue);
        font-family: "IBM Plex Mono", monospace;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 0.04em;
        padding: 4px 6px 18px 6px;
    }

    .ep-sidebar-brand .small {
        display: block;
        color: var(--muted);
        font-size: 8px;
        font-weight: 500;
        letter-spacing: 0.16em;
        margin-top: 6px;
    }

    .ep-sidebar-section {
        color: var(--muted);
        font-family: "IBM Plex Mono", monospace;
        font-size: 8px;
        font-weight: 600;
        letter-spacing: 0.14em;
        margin: 15px 6px 7px 6px;
    }

    section[data-testid="stSidebar"]
    [data-testid="stRadio"] {
        margin-top: 0;
    }

    section[data-testid="stSidebar"]
    [data-testid="stRadio"] label {
        border: 1px solid transparent;
        border-radius: 0 !important;
        padding: 8px 8px !important;
        margin-bottom: 2px !important;
        color: var(--muted2) !important;
        font-family: "IBM Plex Mono", monospace !important;
        font-size: 10px !important;
        letter-spacing: 0.05em;
    }

    section[data-testid="stSidebar"]
    [data-testid="stRadio"] label:hover {
        background: var(--panel2);
        border-color: var(--line);
        color: var(--text) !important;
    }

    section[data-testid="stSidebar"]
    [data-testid="stRadio"] label:has(input:checked) {
        background: #0B1825 !important;
        border-color: #24435A !important;
        color: var(--blue) !important;
    }

    section[data-testid="stSidebar"]
    [data-testid="stRadio"] label p {
        font-family: "IBM Plex Mono", monospace !important;
        font-size: 10px !important;
    }

    /* ========================================================
       SEARCH
       ======================================================== */

    .ep-search-title {
        color: var(--blue);
        font-family: "IBM Plex Mono", monospace;
        font-size: 9px;
        font-weight: 600;
        letter-spacing: 0.12em;
        margin-bottom: 5px;
    }

    section[data-testid="stSidebar"] input {
        background: #080D16 !important;
        border: 1px solid var(--line) !important;
        border-radius: 0 !important;
        color: var(--text) !important;
        font-family: "IBM Plex Mono", monospace !important;
        font-size: 10px !important;
    }

    section[data-testid="stSidebar"] button {
        border-radius: 0 !important;
        font-family: "IBM Plex Mono", monospace !important;
        font-size: 9px !important;
        letter-spacing: 0.08em;
    }

    .ep-query-box {
        background: #080D16;
        border: 1px solid var(--line);
        padding: 10px;
        margin-top: 10px;
    }

    .ep-query-title {
        color: var(--blue);
        font-family: "IBM Plex Mono", monospace;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
    }

    .ep-query-row {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        border-bottom: 1px solid var(--line2);
        padding: 6px 0;
        color: var(--muted);
        font-family: "IBM Plex Mono", monospace;
        font-size: 9px;
    }

    .ep-query-row strong {
        color: var(--text);
        font-weight: 600;
        text-align: right;
    }

    .ep-query-section {
        border-top: 1px solid var(--line);
        margin-top: 10px;
        padding-top: 9px;
    }

    .ep-query-label {
        color: var(--muted);
        font-family: "IBM Plex Mono", monospace;
        font-size: 8px;
        letter-spacing: 0.1em;
        margin-bottom: 5px;
    }

    .ep-query-body {
        color: #CBD5E1;
        font-size: 10px;
        line-height: 1.5;
    }

    .ep-query-direction {
        color: var(--blue);
        font-family: "IBM Plex Mono", monospace;
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 7px;
    }

    .ep-query-detail {
        border-top: 1px solid var(--line2);
        margin-top: 7px;
        padding-top: 7px;
        color: #CBD5E1;
        font-size: 9px;
        line-height: 1.45;
    }

    .ep-query-error {
        color: var(--red);
    }

    /* ========================================================
       TOP TAPE
       ======================================================== */

    .ep-tape {
        width: 100%;
        height: 29px;
        overflow: hidden;
        white-space: nowrap;
        border-top: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        background: #080D16;
        color: var(--muted2);
        font-family: "IBM Plex Mono", monospace;
        font-size: 9px;
        display: flex;
        align-items: center;
        gap: 22px;
        padding: 0 10px;
    }

    .ep-tape-item {
        display: inline-flex;
        gap: 7px;
        align-items: center;
    }

    .ep-tape-item b {
        color: var(--text);
        font-weight: 500;
    }

    .ep-green {
        color: var(--green);
    }

    .ep-red {
        color: var(--red);
    }

    /* ========================================================
       HEADER
       ======================================================== */

    .ep-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 17px 2px 15px 2px;
        border-bottom: 1px solid var(--line);
        margin-bottom: 13px;
    }

    .ep-logo {
        display: flex;
        align-items: center;
        height: 30px;
    }

    .ep-eve {
        color: var(--blue);
        font-family: "IBM Plex Mono", monospace;
        font-size: 24px;
        font-weight: 700;
        letter-spacing: -0.09em;
    }

    .ep-pulse {
        display: inline-flex;
        align-items: center;
        height: 28px;
        margin: 0 3px;
    }

    .ep-wordmark-rest {
        color: var(--blue);
        font-family: "IBM Plex Mono", monospace;
        font-size: 24px;
        font-weight: 700;
        letter-spacing: -0.06em;
    }

    .ep-subtitle {
        color: var(--muted);
        font-family: "IBM Plex Mono", monospace;
        font-size: 8px;
        letter-spacing: 0.13em;
        margin-top: 3px;
    }

    .ep-session {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .ep-session-pill {
        border: 1px solid var(--line);
        color: var(--muted2);
        font-family: "IBM Plex Mono", monospace;
        font-size: 8px;
        letter-spacing: 0.06em;
        padding: 6px 9px;
    }

    .ep-kill {
        border: 1px solid #7F3030;
        color: var(--red);
        font-family: "IBM Plex Mono", monospace;
        font-size: 8px;
        letter-spacing: 0.08em;
        padding: 6px 10px;
    }

    /* ========================================================
       TERMINAL PANELS
       ======================================================== */

    .ep-section-title {
        color: var(--blue);
        font-family: "IBM Plex Mono", monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.12em;
        margin: 4px 0 10px 0;
    }

    .ep-panel {
        background: rgba(8, 13, 22, 0.92);
        border: 1px solid var(--line);
        min-height: 100%;
        padding: 13px;
    }

    .ep-panel-label {
        color: var(--muted);
        font-family: "IBM Plex Mono", monospace;
        font-size: 8px;
        letter-spacing: 0.12em;
        margin-bottom: 8px;
    }

    .ep-panel-value {
        color: var(--text);
        font-family: "IBM Plex Mono", monospace;
        font-size: 20px;
        font-weight: 600;
        letter-spacing: -0.03em;
    }

    .ep-panel-small {
        color: var(--muted2);
        font-family: "IBM Plex Mono", monospace;
        font-size: 9px;
        margin-top: 6px;
    }

    .ep-blue {
        color: var(--blue);
    }

    .ep-positive {
        color: var(--green);
    }

    .ep-negative {
        color: var(--red);
    }

    .ep-warning {
        color: var(--yellow);
    }

    /* ========================================================
       TABLES
       ======================================================== */

    .ep-table {
        width: 100%;
        border-collapse: collapse;
        font-family: "IBM Plex Mono", monospace;
        font-size: 9px;
    }

    .ep-table th {
        color: var(--muted);
        text-align: left;
        font-weight: 500;
        letter-spacing: 0.07em;
        padding: 8px 7px;
        border-bottom: 1px solid var(--line);
    }

    .ep-table td {
        color: var(--text);
        padding: 8px 7px;
        border-bottom: 1px solid var(--line2);
        vertical-align: top;
    }

    .ep-table tr:hover td {
        background: rgba(56,189,248,0.025);
    }

    /* ========================================================
       PIPELINE
       ======================================================== */

    .ep-pipeline {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        border: 1px solid var(--line);
        background: #080D16;
    }

    .ep-pipeline-cell {
        padding: 12px;
        border-right: 1px solid var(--line);
    }

    .ep-pipeline-cell:last-child {
        border-right: none;
    }

    .ep-pipeline-number {
        color: var(--text);
        font-family: "IBM Plex Mono", monospace;
        font-size: 21px;
        font-weight: 600;
    }

    .ep-pipeline-label {
        color: var(--muted);
        font-family: "IBM Plex Mono", monospace;
        font-size: 8px;
        letter-spacing: 0.1em;
        margin-top: 4px;
    }

    /* ========================================================
       FOOTER
       ======================================================== */

    .ep-footer {
        border-top: 1px solid var(--line);
        margin-top: 30px;
        padding-top: 10px;
        color: var(--muted);
        font-family: "IBM Plex Mono", monospace;
        font-size: 8px;
        letter-spacing: 0.08em;
    }

    @media (max-width: 900px) {
        .ep-header {
            align-items: flex-start;
            gap: 12px;
            flex-direction: column;
        }

        .ep-pipeline {
            grid-template-columns: repeat(2, 1fr);
        }

        .ep-pipeline-cell {
            border-bottom: 1px solid var(--line);
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_ticker(value):
    value = str(value or "").upper().strip()

    if value.startswith("R") and len(value) > 1:
        return value[1:]

    return value


def load_pipeline():
    if not PIPELINE_FILE.exists():
        return {}

    try:
        return json.loads(
            PIPELINE_FILE.read_text()
        )
    except Exception:
        return {}


def get_all_theses_for_ticker(ticker):
    ticker = normalize_ticker(ticker)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                created_at,
                ticker,
                direction,
                confidence,
                thesis,
                catalyst,
                bull_case,
                bear_case,
                invalidation_condition,
                expected_horizon,
                entry_price,
                current_price,
                return_pct,
                status,
                resolved_at,
                resolution_reason
            FROM theses
            WHERE UPPER(ticker) = ?
               OR UPPER(ticker) = ?
            ORDER BY id DESC
            """,
            (
                ticker,
                "r" + ticker,
            ),
        )

        rows = cursor.fetchall()
        conn.close()

        return rows

    except Exception:
        return []


def get_latest_trade_for_ticker(ticker):
    ticker = normalize_ticker(ticker)

    try:
        rows = get_trades()
    except Exception:
        return None

    for row in reversed(rows):
        if len(row) < 9:
            continue

        if normalize_ticker(row[2]) == ticker:
            return {
                "id": row[0],
                "timestamp": row[1],
                "ticker": row[2],
                "side": row[3],
                "quantity": safe_float(row[4]),
                "price": safe_float(row[5]),
                "value": safe_float(row[6]),
                "confidence": safe_float(row[7]),
                "reasoning": row[8] or "",
            }

    return None


def get_latest_thesis_for_ticker(ticker):
    rows = get_all_theses_for_ticker(ticker)

    if not rows:
        return None

    row = rows[0]

    return {
        "id": row[0],
        "created_at": row[1],
        "ticker": row[2],
        "direction": row[3],
        "confidence": safe_float(row[4]),
        "thesis": row[5] or "",
        "catalyst": row[6] or "",
        "bull_case": row[7] or "",
        "bear_case": row[8] or "",
        "invalidation": row[9] or "",
        "horizon": row[10] or "",
        "entry_price": safe_float(row[11]),
        "current_price": safe_float(row[12]),
        "return_pct": safe_float(row[13]),
        "status": row[14] or "",
        "resolved_at": row[15],
        "resolution_reason": row[16] or "",
    }


def known_tickers():
    tickers = set()

    try:
        initial = load_initial_portfolio()

        for symbol in initial:
            tickers.add(
                normalize_ticker(symbol)
            )
    except Exception:
        pass

    try:
        for row in get_trades():
            if len(row) >= 3:
                tickers.add(
                    normalize_ticker(row[2])
                )
    except Exception:
        pass

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT ticker
            FROM theses
            """
        )

        for row in cursor.fetchall():
            if row and row[0]:
                tickers.add(
                    normalize_ticker(row[0])
                )

        conn.close()

    except Exception:
        pass

    return tickers


def extract_ticker(query):
    query = str(query or "").upper()

    tickers = known_tickers()

    for ticker in sorted(
        tickers,
        key=len,
        reverse=True,
    ):
        if re.search(
            rf"\b{re.escape(ticker)}\b",
            query,
        ):
            return ticker

    return None


def answer_agent_query(query):
    query = str(query or "").strip()

    if not query:
        return {
            "found": False,
            "title": "NO QUERY",
            "body": "Enter a ticker and ask why the agent acted.",
        }

    ticker = extract_ticker(query)

    if not ticker:
        return {
            "found": False,
            "title": "TICKER NOT FOUND",
            "body": (
                "Mention a ticker such as NVDA, AAPL, MSFT, "
                "META, AMD or GOOGL."
            ),
        }

    trade = get_latest_trade_for_ticker(ticker)
    thesis = get_latest_thesis_for_ticker(ticker)

    if not trade and not thesis:
        return {
            "found": False,
            "title": f"{ticker} NOT FOUND",
            "body": (
                "No trade or investment thesis was found "
                "for this ticker."
            ),
        }

    return {
        "found": True,
        "ticker": ticker,
        "trade": trade,
        "thesis": thesis,
    }


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    """
    <div class="ep-sidebar-brand">
        EVENTPULSE
        <span class="small">CONTROL TERMINAL</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div class="ep-sidebar-section">NAVIGATION</div>',
    unsafe_allow_html=True,
)

section = st.sidebar.radio(
    "NAVIGATION",
    [
        "OVERVIEW",
        "PORTFOLIO",
        "EVENTS",
        "COUNCIL",
        "RISK",
        "EXECUTION",
        "THESES",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

st.sidebar.markdown(
    '<div class="ep-sidebar-section">AGENT REASONING</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div class="ep-search-title">ASK WHY THE AGENT ACTED</div>',
    unsafe_allow_html=True,
)

agent_query = st.sidebar.text_input(
    "Agent reasoning query",
    placeholder="Why did it buy NVDA?",
    label_visibility="collapsed",
    key="agent_reasoning_query",
)

if st.sidebar.button(
    "QUERY AGENT",
    use_container_width=True,
):
    st.session_state["agent_query_result"] = (
        answer_agent_query(agent_query)
    )


query_result = st.session_state.get(
    "agent_query_result"
)

if query_result:

    st.sidebar.markdown(
        '<div class="ep-query-box">',
        unsafe_allow_html=True,
    )

    if not query_result.get("found"):

        st.sidebar.markdown(
            f"""
            <div class="ep-query-title ep-query-error">
                {query_result.get("title", "ERROR")}
            </div>

            <div class="ep-query-body">
                {query_result.get("body", "")}
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        ticker = query_result["ticker"]
        trade = query_result.get("trade")
        thesis = query_result.get("thesis")

        st.sidebar.markdown(
            f"""
            <div class="ep-query-title">
                AGENT REASONING · {ticker}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if trade:

            side = str(
                trade["side"]
            ).upper()

            confidence = (
                trade["confidence"] * 100
            )

            st.sidebar.markdown(
                f"""
                <div class="ep-query-row">
                    <span>SIDE</span>
                    <strong>{side}</strong>
                </div>

                <div class="ep-query-row">
                    <span>PRICE</span>
                    <strong>${trade["price"]:,.2f}</strong>
                </div>

                <div class="ep-query-row">
                    <span>QUANTITY</span>
                    <strong>{trade["quantity"]:,.6f}</strong>
                </div>

                <div class="ep-query-row">
                    <span>NOTIONAL</span>
                    <strong>${trade["value"]:,.2f}</strong>
                </div>

                <div class="ep-query-row">
                    <span>CONFIDENCE</span>
                    <strong>{confidence:.0f}%</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if thesis:

            st.sidebar.markdown(
                """
                <div class="ep-query-section">
                    <div class="ep-query-label">
                        COUNCIL DECISION
                    </div>
                """,
                unsafe_allow_html=True,
            )

            st.sidebar.markdown(
                f"""
                <div class="ep-query-direction">
                    {thesis["direction"]}
                </div>

                <div class="ep-query-body">
                    {thesis["thesis"] or "No thesis recorded."}
                </div>
                """,
                unsafe_allow_html=True,
            )

            details = [
                ("CATALYST", thesis["catalyst"]),
                ("BULL CASE", thesis["bull_case"]),
                ("BEAR CASE", thesis["bear_case"]),
                ("INVALIDATION", thesis["invalidation"]),
                ("HORIZON", thesis["horizon"]),
            ]

            for label, value in details:

                if value:

                    st.sidebar.markdown(
                        f"""
                        <div class="ep-query-detail">
                            <div class="ep-query-label">
                                {label}
                            </div>
                            {value}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.sidebar.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        if trade and trade["reasoning"]:

            st.sidebar.markdown(
                f"""
                <div class="ep-query-section">
                    <div class="ep-query-label">
                        EXECUTION REASON
                    </div>

                    <div class="ep-query-body">
                        {trade["reasoning"]}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if thesis and thesis["status"]:

            st.sidebar.markdown(
                f"""
                <div class="ep-query-row">
                    <span>THESIS STATUS</span>
                    <strong>{thesis["status"]}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.sidebar.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# LOAD CORE DATA
# ============================================================

try:
    cash, positions = load_portfolio()
except Exception:
    cash = 0.0
    positions = {}

try:
    initial_positions = load_initial_portfolio()
except Exception:
    initial_positions = {}

try:
    trades = get_trades()
except Exception:
    trades = []

try:
    equity_history = get_equity_history()
except Exception:
    equity_history = []

try:
    open_theses = get_open_theses()
except Exception:
    open_theses = []

try:
    events = get_events()
except Exception:
    events = []

pipeline = load_pipeline()

latest_equity = INITIAL_EQUITY

if equity_history:

    try:
        latest_equity = safe_float(
            equity_history[-1][-1],
            INITIAL_EQUITY,
        )
    except Exception:
        latest_equity = INITIAL_EQUITY

return_pct = (
    (latest_equity / INITIAL_EQUITY) - 1
) * 100

pnl = latest_equity - INITIAL_EQUITY

invested_value = 0.0

for symbol, position in positions.items():

    try:

        if isinstance(position, dict):

            quantity = safe_float(
                position.get("quantity")
            )

            price = safe_float(
                position.get("average_price")
            )

        else:

            quantity = safe_float(position)

            price = 0.0

        invested_value += quantity * price

    except Exception:
        pass

invested_pct = (
    invested_value / latest_equity * 100
    if latest_equity > 0
    else 0
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="ep-tape">

        <span class="ep-tape-item">
            REALITY MARKET
            <b>LIVE</b>
        </span>

        <span class="ep-tape-item">
            UNIVERSE
            <b>1173</b>
        </span>

        <span class="ep-tape-item">
            SCREEN
            <b>50</b>
        </span>

        <span class="ep-tape-item">
            RESEARCH
            <b>10</b>
        </span>

        <span class="ep-tape-item">
            QWEN
            <b>ACTIVE</b>
        </span>

        <span class="ep-tape-item">
            EXECUTION
            <b>PAPER</b>
        </span>

    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="ep-header">

        <div>
            <div class="ep-logo">

                <span class="ep-eve">EVE</span>

                <span class="ep-pulse">
                    <svg
                        width="78"
                        height="28"
                        viewBox="0 0 78 28"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <polyline
                            points="
                                0,15
                                14,15
                                20,15
                                24,5
                                29,23
                                35,15
                                47,15
                                51,10
                                55,18
                                60,15
                                78,15
                            "
                            fill="none"
                            stroke="#38BDF8"
                            stroke-width="1.7"
                            stroke-linecap="square"
                            stroke-linejoin="miter"
                        />
                    </svg>
                </span>

                <span class="ep-wordmark-rest">
                    NTPULSE
                </span>

            </div>

            <div class="ep-subtitle">
                AUTONOMOUS EVENT-DRIVEN TRADING
            </div>
        </div>

        <div class="ep-session">

            <span class="ep-session-pill">
                US CASH CLOSED · rTOKEN 24H LIVE
            </span>

            <span class="ep-kill">
                KILL
            </span>

        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SECTION: OVERVIEW
# ============================================================

if section == "OVERVIEW":

    st.markdown(
        '<div class="ep-section-title">SYSTEM OVERVIEW</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    overview_cards = [
        (
            c1,
            "EQUITY",
            f"${latest_equity:,.2f}",
            f"{return_pct:+.2f}%",
            "positive" if return_pct >= 0 else "negative",
        ),
        (
            c2,
            "CASH",
            f"${safe_float(cash):,.2f}",
            "AVAILABLE",
            "",
        ),
        (
            c3,
            "INVESTED",
            f"{invested_pct:.1f}%",
            "PORTFOLIO",
            "",
        ),
        (
            c4,
            "TRADES",
            str(len(trades)),
            "PAPER FILLS",
            "",
        ),
        (
            c5,
            "THESIS",
            str(len(open_theses)),
            "OPEN",
            "",
        ),
    ]

    for col, label, value, small, cls in overview_cards:

        col.markdown(
            f"""
            <div class="ep-panel">

                <div class="ep-panel-label">
                    {label}
                </div>

                <div class="ep-panel-value {cls}">
                    {value}
                </div>

                <div class="ep-panel-small">
                    {small}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    pipeline_cells = [
        (
            "REALITY UNIVERSE",
            pipeline.get("reality_universe", 1173),
        ),
        (
            "FAST SCREEN",
            pipeline.get("fast_screen", 50),
        ),
        (
            "RESEARCH",
            pipeline.get("evidence_research", 10),
        ),
        (
            "QWEN COUNCIL",
            pipeline.get("qwen_council", 0),
        ),
        (
            "PAPER EXECUTION",
            pipeline.get(
                "paper_execution",
                {},
            ).get("filled", 0),
        ),
    ]

    pipeline_html = """
    <div class="ep-pipeline">
    """

    for label, value in pipeline_cells:

        pipeline_html += f"""
        <div class="ep-pipeline-cell">

            <div class="ep-pipeline-number">
                {value}
            </div>

            <div class="ep-pipeline-label">
                {label}
            </div>

        </div>
        """

    pipeline_html += "</div>"

    st.markdown(
        pipeline_html,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1])

    with left:

        st.markdown(
            '<div class="ep-section-title">QWEN DECISION FLOW</div>',
            unsafe_allow_html=True,
        )

        counts = pipeline.get(
            "decision_counts",
            {},
        )

        rows = []

        for direction in [
            "BUY",
            "SELL",
            "HOLD",
            "WAIT",
        ]:

            rows.append(
                {
                    "Decision": direction,
                    "Count": counts.get(
                        direction,
                        0,
                    ),
                }
            )

        df = pd.DataFrame(rows)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

    with right:

        st.markdown(
            '<div class="ep-section-title">RISK GATE</div>',
            unsafe_allow_html=True,
        )

        risk = pipeline.get(
            "risk",
            {},
        )

        execution = pipeline.get(
            "paper_execution",
            {},
        )

        st.markdown(
            f"""
            <div class="ep-panel">

                <div class="ep-query-row">
                    <span>REVIEWED</span>
                    <strong>
                        {risk.get("reviewed", 0)}
                    </strong>
                </div>

                <div class="ep-query-row">
                    <span>APPROVED</span>
                    <strong class="ep-positive">
                        {risk.get("approved", 0)}
                    </strong>
                </div>

                <div class="ep-query-row">
                    <span>BLOCKED</span>
                    <strong class="ep-negative">
                        {risk.get("blocked", 0)}
                    </strong>
                </div>

                <div class="ep-query-row">
                    <span>ORDERS ATTEMPTED</span>
                    <strong>
                        {execution.get("attempted", 0)}
                    </strong>
                </div>

                <div class="ep-query-row">
                    <span>FILLED</span>
                    <strong class="ep-positive">
                        {execution.get("filled", 0)}
                    </strong>
                </div>

                <div class="ep-query-row">
                    <span>FAILED</span>
                    <strong class="ep-negative">
                        {execution.get("failed", 0)}
                    </strong>
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# SECTION: PORTFOLIO
# ============================================================

elif section == "PORTFOLIO":

    st.markdown(
        '<div class="ep-section-title">PORTFOLIO TERMINAL</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 2])

    with left:

        st.markdown(
            f"""
            <div class="ep-panel">

                <div class="ep-panel-label">
                    TOTAL EQUITY
                </div>

                <div class="ep-panel-value">
                    ${latest_equity:,.2f}
                </div>

                <div class="ep-panel-small">
                    {return_pct:+.2f}% SINCE INCEPTION
                </div>

                <br>

                <div class="ep-query-row">
                    <span>CASH</span>
                    <strong>
                        ${safe_float(cash):,.2f}
                    </strong>
                </div>

                <div class="ep-query-row">
                    <span>INVESTED</span>
                    <strong>
                        {invested_pct:.1f}%
                    </strong>
                </div>

                <div class="ep-query-row">
                    <span>POSITIONS</span>
                    <strong>
                        {len(positions)}
                    </strong>
                </div>

                <div class="ep-query-row">
                    <span>TRADES</span>
                    <strong>
                        {len(trades)}
                    </strong>
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:

        rows = []

        for symbol, position in positions.items():

            if isinstance(position, dict):

                quantity = safe_float(
                    position.get("quantity")
                )

                average_price = safe_float(
                    position.get("average_price")
                )

            else:

                quantity = safe_float(position)
                average_price = 0.0

            rows.append(
                {
                    "TOKEN": symbol,
                    "UNDERLYING": normalize_ticker(
                        symbol
                    ),
                    "QTY": quantity,
                    "AVG PRICE": average_price,
                    "COST BASIS": quantity * average_price,
                }
            )

        if rows:

            df = pd.DataFrame(rows)

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# SECTION: EVENTS
# ============================================================

elif section == "EVENTS":

    st.markdown(
        '<div class="ep-section-title">EVENT FEED</div>',
        unsafe_allow_html=True,
    )

    if not events:

        st.markdown(
            """
            <div class="ep-panel">
                <div class="ep-panel-label">
                    EVENT FEED
                </div>
                <div class="ep-panel-small">
                    No events recorded.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        rows = []

        for event in events:

            if isinstance(event, dict):

                rows.append(
                    {
                        "TIME": event.get(
                            "timestamp",
                            event.get(
                                "published_at",
                                "",
                            ),
                        ),
                        "TICKER": event.get(
                            "ticker",
                            "",
                        ),
                        "HEADLINE": event.get(
                            "headline",
                            event.get(
                                "title",
                                "",
                            ),
                        ),
                        "RELEVANCE": event.get(
                            "relevance",
                            "",
                        ),
                    }
                )

            elif isinstance(event, (tuple, list)):

                rows.append(
                    {
                        "TIME": (
                            event[0]
                            if len(event) > 0
                            else ""
                        ),
                        "TICKER": (
                            event[1]
                            if len(event) > 1
                            else ""
                        ),
                        "HEADLINE": (
                            event[2]
                            if len(event) > 2
                            else ""
                        ),
                        "RELEVANCE": (
                            event[3]
                            if len(event) > 3
                            else ""
                        ),
                    }
                )

        if rows:

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# SECTION: COUNCIL
# ============================================================

elif section == "COUNCIL":

    st.markdown(
        '<div class="ep-section-title">QWEN INVESTMENT COUNCIL</div>',
        unsafe_allow_html=True,
    )

    counts = pipeline.get(
        "decision_counts",
        {},
    )

    c1, c2, c3, c4 = st.columns(4)

    council_cards = [
        (c1, "BUY", counts.get("BUY", 0)),
        (c2, "SELL", counts.get("SELL", 0)),
        (c3, "HOLD", counts.get("HOLD", 0)),
        (c4, "WAIT", counts.get("WAIT", 0)),
    ]

    for col, label, value in council_cards:

        col.markdown(
            f"""
            <div class="ep-panel">

                <div class="ep-panel-label">
                    {label}
                </div>

                <div class="ep-panel-value">
                    {value}
                </div>

                <div class="ep-panel-small">
                    COUNCIL SIGNALS
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    finalists = pipeline.get(
        "finalists",
        [],
    )

    if finalists:

        rows = []

        for item in finalists:

            rows.append(
                {
                    "TICKER": item.get(
                        "ticker",
                        "",
                    ),
                    "EXECUTION": item.get(
                        "execution_symbol",
                        "",
                    ),
                    "FAST": item.get(
                        "fast_score",
                        0,
                    ),
                    "EVIDENCE": item.get(
                        "evidence_score",
                        0,
                    ),
                    "PRICE": item.get(
                        "last_price",
                        0,
                    ),
                    "24H": item.get(
                        "change_24h_pct",
                        0,
                    ),
                    "TURNOVER": item.get(
                        "turnover_24h",
                        0,
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.markdown(
            """
            <div class="ep-panel">
                <div class="ep-panel-small">
                    No council snapshot available yet.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# SECTION: RISK
# ============================================================

elif section == "RISK":

    st.markdown(
        '<div class="ep-section-title">DETERMINISTIC RISK ENGINE</div>',
        unsafe_allow_html=True,
    )

    risk = pipeline.get(
        "risk",
        {},
    )

    c1, c2, c3 = st.columns(3)

    cards = [
        (
            c1,
            "REVIEWED",
            risk.get("reviewed", 0),
        ),
        (
            c2,
            "APPROVED",
            risk.get("approved", 0),
        ),
        (
            c3,
            "BLOCKED",
            risk.get("blocked", 0),
        ),
    ]

    for col, label, value in cards:

        col.markdown(
            f"""
            <div class="ep-panel">

                <div class="ep-panel-label">
                    {label}
                </div>

                <div class="ep-panel-value">
                    {value}
                </div>

                <div class="ep-panel-small">
                    PYTHON RISK GATE
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="ep-panel">

            <div class="ep-query-row">
                <span>MINIMUM CONFIDENCE</span>
                <strong>60%</strong>
            </div>

            <div class="ep-query-row">
                <span>MAX TRADE / PORTFOLIO</span>
                <strong>10%</strong>
            </div>

            <div class="ep-query-row">
                <span>MAX SINGLE POSITION</span>
                <strong>20%</strong>
            </div>

            <div class="ep-query-row">
                <span>MAX DAILY LOSS</span>
                <strong>2%</strong>
            </div>

            <div class="ep-query-row">
                <span>MAX DRAWDOWN</span>
                <strong>10%</strong>
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SECTION: EXECUTION
# ============================================================

elif section == "EXECUTION":

    st.markdown(
        '<div class="ep-section-title">PAPER EXECUTION TERMINAL</div>',
        unsafe_allow_html=True,
    )

    execution = pipeline.get(
        "paper_execution",
        {},
    )

    c1, c2, c3 = st.columns(3)

    cards = [
        (
            c1,
            "ATTEMPTED",
            execution.get("attempted", 0),
        ),
        (
            c2,
            "FILLED",
            execution.get("filled", 0),
        ),
        (
            c3,
            "FAILED",
            execution.get("failed", 0),
        ),
    ]

    for col, label, value in cards:

        col.markdown(
            f"""
            <div class="ep-panel">

                <div class="ep-panel-label">
                    {label}
                </div>

                <div class="ep-panel-value">
                    {value}
                </div>

                <div class="ep-panel-small">
                    PAPER ONLY
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    if trades:

        rows = []

        for row in reversed(trades):

            if len(row) < 9:
                continue

            rows.append(
                {
                    "ID": row[0],
                    "TIME": row[1],
                    "TICKER": row[2],
                    "SIDE": row[3],
                    "QTY": safe_float(row[4]),
                    "PRICE": safe_float(row[5]),
                    "VALUE": safe_float(row[6]),
                    "CONFIDENCE": (
                        safe_float(row[7]) * 100
                    ),
                    "REASON": row[8],
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.markdown(
            """
            <div class="ep-panel">
                <div class="ep-panel-small">
                    No paper executions recorded.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# SECTION: THESES
# ============================================================

elif section == "THESES":

    st.markdown(
        '<div class="ep-section-title">THESIS TRACKING</div>',
        unsafe_allow_html=True,
    )

    if not open_theses:

        st.markdown(
            """
            <div class="ep-panel">
                <div class="ep-panel-small">
                    No open investment theses.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        rows = []

        for row in open_theses:

            if len(row) < 17:
                continue

            rows.append(
                {
                    "ID": row[0],
                    "CREATED": row[1],
                    "TICKER": row[2],
                    "DIRECTION": row[3],
                    "CONFIDENCE": (
                        safe_float(row[4]) * 100
                    ),
                    "THESIS": row[5],
                    "CATALYST": row[6],
                    "HORIZON": row[10],
                    "ENTRY": row[11],
                    "CURRENT": row[12],
                    "RETURN": row[13],
                    "STATUS": row[14],
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="ep-footer">
        EVENTPULSE · QWEN INVESTMENT COUNCIL · DETERMINISTIC RISK ·
        BITGET REALITY PAPER EXECUTION · AUDIT TRAIL ACTIVE
    </div>
    """,
    unsafe_allow_html=True,
)