from datetime import datetime
from pathlib import Path
import json
import sqlite3

import pandas as pd
import streamlit as st

from app.database import (
    get_connection,
    get_initial_cash,
    get_initial_positions,
    get_open_theses,
    get_trades,
    get_qwen_decision_history,
    save_qwen_decision,
    load_initial_portfolio,
    load_portfolio,
    save_portfolio,
)
from app.bitget_universe import (
    rank_candidates,
    universe_summary,
    underlying_ticker,
)
from app.universe_research import research_candidates
from app.council import analyze_event_with_finalists
from app.event_cycle import run_event_driven_cycle
from app.news import get_market_events, get_news
from app.market import get_market_data


# ============================================================
# EVENTPULSE V2 — CONSOLIDATED PREMIUM TERMINAL
# ============================================================

st.set_page_config(
    page_title="EVENTPULSE",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root {
    --void:#07080A;
    --panel:#12151A;
    --panel2:#0D1014;
    --line:#252A31;
    --text:#E5E7EB;
    --muted:#7F8995;
    --teal:#2EE6C8;
    --red:#E23B3B;
    --green:#3DDC97;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--void);
    color: var(--text);
}

/* EVENTPULSE GLOBAL TYPOGRAPHY */

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stSidebar"],
.stMarkdown,
.stText,
.stCaption,
button,
input,
textarea,
select,
[data-baseweb="select"],
[data-testid="stMetric"],
[data-testid="stDataFrame"] {
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif !important;
}

.ep-mono,
.ep-wordmark,
.ep-sub,
.ep-panel-title,
.ep-panel-sub,
.ep-metric-label,
.ep-metric-value,
.ep-stage-label,
.ep-stage-value,
.ep-ticker,
.ep-small,
.ep-status {
    font-family:
        ui-monospace,
        SFMono-Regular,
        Menlo,
        Monaco,
        Consolas,
        monospace !important;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif !important;
}

.ep-deploy {
    border: 1px solid var(--teal);
    background: #0B1111;
    color: var(--teal);
    padding: 11px 13px;
    margin: 8px 0 12px;
    font-family:
        ui-monospace,
        SFMono-Regular,
        Menlo,
        Monaco,
        Consolas,
        monospace;
    font-size: 10px;
    letter-spacing: .10em;
    text-transform: uppercase;
}

.ep-deploy-status {
    color: #7F8995;
    font-family:
        ui-monospace,
        SFMono-Regular,
        Menlo,
        Monaco,
        Consolas,
        monospace;
    font-size: 9px;
    letter-spacing: .08em;
    margin-top: 4px;
}

[data-testid="stHeader"] {
    background: var(--void);
}

.block-container {
    max-width: 1800px;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}

[data-testid="stSidebar"] {
    background: #090B0E;
    border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.2rem;
}

.ep-wordmark {
    font-size: 25px;
    font-weight: 800;
    letter-spacing: .12em;
    color: var(--text);
    margin-bottom: 2px;
}

.ep-sub {
    color: var(--muted);
    font-size: 9px;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin-bottom: 28px;
}

.ep-section {
    color: var(--muted);
    font-size: 9px;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin: 20px 0 8px;
}

.ep-status {
    border: 1px solid var(--line);
    background: var(--panel2);
    color: var(--muted);
    padding: 6px 8px;
    margin: 4px 0;
    font-size: 9px;
    letter-spacing: .08em;
}

.ep-kill {
    border: 1px solid var(--red);
    color: var(--red);
    padding: 8px;
    text-align: center;
    font-size: 10px;
    letter-spacing: .12em;
    margin-top: 10px;
}

.ep-title {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -.02em;
}

.ep-muted {
    color: var(--muted);
}

.ep-panel {
    background: var(--panel);
    border: 1px solid var(--line);
    padding: 16px;
    min-height: 100%;
}

.ep-panel-tall {
    min-height: 510px;
}

.ep-panel-title {
    font-size: 11px;
    letter-spacing: .11em;
    font-weight: 700;
    color: var(--text);
}

.ep-panel-sub {
    color: var(--muted);
    font-size: 9px;
    letter-spacing: .08em;
    margin-top: 3px;
    margin-bottom: 15px;
}

.ep-metric {
    background: var(--panel);
    border: 1px solid var(--line);
    padding: 13px;
    min-height: 94px;
}

.ep-metric-label {
    color: var(--muted);
    font-size: 9px;
    letter-spacing: .1em;
}

.ep-metric-value {
    font-size: 22px;
    font-weight: 700;
    margin-top: 8px;
}

.ep-metric-caption {
    color: var(--muted);
    font-size: 9px;
    margin-top: 5px;
}

.ep-negative {
    color: var(--red);
}

.ep-positive {
    color: var(--green);
}

.ep-live {
    color: var(--teal);
    border: 1px solid rgba(46,230,200,.35);
    padding: 2px 5px;
    font-size: 8px;
    letter-spacing: .08em;
}

.ep-stage {
    background: var(--panel);
    border: 1px solid var(--line);
    padding: 11px 9px;
    text-align: center;
    min-height: 62px;
}

.ep-stage-label {
    color: var(--muted);
    font-size: 8px;
    letter-spacing: .08em;
}

.ep-stage-value {
    color: var(--teal);
    font-size: 17px;
    font-weight: 700;
    margin-top: 5px;
}

.ep-arrow {
    color: var(--teal);
    text-align: center;
    padding-top: 22px;
}

.ep-note {
    background: var(--panel2);
    border: 1px solid var(--line);
    padding: 12px;
    color: var(--muted);
    font-size: 10px;
    line-height: 1.5;
}

.ep-tape-wrap {
    overflow: hidden;
    white-space: nowrap;
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    background: #090B0E;
    padding: 9px 0;
    margin: 15px 0;
}

.ep-tape {
    display: inline-flex;
    gap: 28px;
    animation: ep-scroll 45s linear infinite;
}

.ep-tape:hover {
    animation-play-state: paused;
}

.ep-tape-item {
    font-family: monospace;
    font-size: 11px;
}

@keyframes ep-scroll {
    from { transform: translateX(0); }
    to { transform: translateX(-50%); }
}

.ep-row {
    border-bottom: 1px solid #1D2228;
    padding: 8px 0;
    font-family: monospace;
    font-size: 11px;
}

.ep-small {
    font-size: 9px;
    color: var(--muted);
}

.ep-score {
    color: var(--teal);
    font-family: monospace;
}

div[data-testid="stButton"] > button {
    background: transparent;
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 2px;
    min-height: 30px;
}

div[data-testid="stButton"] > button:hover {
    border-color: var(--teal);
    color: var(--teal);
}

[data-baseweb="select"] > div {
    background: var(--panel2);
    border-color: var(--line);
}

.stTextInput input {
    background: var(--panel2);
    color: var(--text);
    border-color: var(--line);
}

hr {
    border-color: var(--line);
    opacity: .55;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
}

/* ============================================================
   EVENTPULSE UI BUILD 01
   Controlled visual refinement — no layout or logic changes.
   ============================================================ */

html, body, [data-testid="stAppViewContainer"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.block-container {
    max-width: 1760px;
    padding-left: 2.0rem;
    padding-right: 2.0rem;
    padding-top: 1.35rem;
}

[data-testid="stSidebar"] {
    width: 228px;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    line-height: 1.25;
}

.ep-wordmark {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 23px;
    letter-spacing: .16em;
}

.ep-sub {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 8px;
    letter-spacing: .12em;
    line-height: 1.5;
}

.ep-title {
    font-size: 24px;
    letter-spacing: -.025em;
    font-weight: 650;
}

.ep-panel {
    background: #101318;
    border: 1px solid #292E35;
    padding: 17px;
}

.ep-panel-title {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 10px;
    letter-spacing: .13em;
}

.ep-panel-sub {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 8px;
    letter-spacing: .10em;
}

.ep-metric {
    background: #101318;
    border: 1px solid #292E35;
    padding: 15px;
    min-height: 98px;
}

.ep-metric-label,
.ep-metric-caption,
.ep-small,
.ep-stage-label {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.ep-metric-label {
    font-size: 8px;
    letter-spacing: .12em;
}

.ep-metric-value {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 21px;
    letter-spacing: -.03em;
}

.ep-stage {
    background: #101318;
    border-color: #292E35;
    padding: 12px 8px;
}

.ep-stage-value {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.ep-note {
    background: #0B0E12;
    border-color: #292E35;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 9px;
}

.ep-tape-wrap {
    background: #080A0D;
    border-color: #292E35;
    margin: 17px 0;
}

.ep-tape-item {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 10px;
}

.ep-row {
    border-bottom-color: #20252C;
    padding: 9px 0;
}

div[data-testid="stButton"] > button {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 10px;
    letter-spacing: .035em;
    background: #0D1014;
    border-color: #292E35;
    min-height: 32px;
    transition: border-color .15s ease, color .15s ease, background .15s ease;
}

div[data-testid="stButton"] > button:hover {
    background: #11171A;
    border-color: var(--teal);
    color: var(--teal);
}

[data-baseweb="select"] > div {
    min-height: 38px;
    background: #0D1014;
    border-color: #292E35;
}

[data-baseweb="select"] input {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    justify-content: flex-start;
    text-align: left;
    border-color: transparent;
    background: transparent;
    min-height: 34px;
    padding-left: 10px;
}

[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
    background: #101419;
    border-color: #252B31;
}

.ep-panel-tall {
    min-height: 540px;
}


    .ep-event-detail {
        border: 1px solid #252A31;
        background: #0D1014;
        padding: 18px;
        margin: 14px 0;
    }

    .ep-event-detail-top {
        display: flex;
        gap: 8px;
        align-items: center;
        margin-bottom: 12px;
    }

    .ep-event-ticker {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: .08em;
        color: #2EE6C8;
    }

    .ep-event-headline {
        font-size: 21px;
        line-height: 1.3;
        color: #E7EBEF;
        font-weight: 600;
        margin-bottom: 18px;
    }

    .ep-event-label,
    .ep-section-label {
        font-size: 10px;
        letter-spacing: .12em;
        color: #7D8792;
        margin-top: 14px;
        margin-bottom: 8px;
    }

    .ep-event-reason {
        color: #AAB2BC;
        font-size: 13px;
        line-height: 1.55;
    }

    .ep-inline-note {
        border: 1px solid #20252B;
        background: #0B0E12;
        padding: 12px 14px;
        color: #89939E;
        font-size: 12px;
        line-height: 1.5;
        min-height: 42px;
    }

    .ep-inline-note strong {
        color: #DCE2E8;
    }

    .ep-event-row {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        border-top: 1px solid #20252B;
        padding: 14px 4px;
    }

    .ep-event-row-left {
        min-width: 0;
    }

    .ep-event-row-ticker {
        color: #2EE6C8;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: .08em;
        margin-bottom: 4px;
    }

    .ep-event-row-title {
        color: #DCE2E8;
        font-size: 13px;
        line-height: 1.4;
    }

    .ep-event-row-reason {
        color: #707A85;
        font-size: 11px;
        margin-top: 5px;
    }

    .ep-event-row-right {
        flex: 0 0 90px;
        text-align: right;
        color: #AAB2BC;
        font-size: 12px;
    }

    .ep-badge {
        display: inline-block;
        border: 1px solid #343A42;
        padding: 3px 7px;
        font-size: 9px;
        letter-spacing: .08em;
        color: #AAB2BC;
        margin-left: 5px;
    }

    .ep-positive {
        color: #3DDC97;
        border-color: #245A49;
    }

    .ep-negative {
        color: #E23B3B;
        border-color: #633033;
    }

    .ep-neutral {
        color: #AAB2BC;
        border-color: #343A42;
    }

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================


def execute_live_agent_cycle(execute_paper=False):
    """Dashboard entry point for the canonical EventPulse cycle."""
    return run_event_driven_cycle(
        execute_paper=execute_paper
    )


def money(value):
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "—"


def pct(value):
    try:
        v = float(value)
        cls = "ep-positive" if v >= 0 else "ep-negative"
        sign = "+" if v >= 0 else ""
        return f'<span class="{cls}">{sign}{v:.2f}%</span>'
    except Exception:
        return "—"


def portfolio_dict():
    cash, positions = load_portfolio()
    return {
        "cash": float(cash or 0),
        "positions": positions or {},
    }


def row_ticker(row):
    return (
        row.get("ticker")
        or row.get("underlying")
        or row.get("asset")
        or row.get("symbol")
        or ""
    )


def row_price(row):
    for key in ("price", "last", "current_price", "entry_price"):
        if row.get(key) is not None:
            try:
                return float(row[key])
            except Exception:
                pass
    td = row.get("ticker_data") or {}
    try:
        return float(td.get("last"))
    except Exception:
        return 0.0


def row_change(row):
    for key in ("change_pct", "move_pct", "change", "return_pct"):
        if row.get(key) is not None:
            try:
                return float(row[key])
            except Exception:
                pass
    td = row.get("ticker_data") or {}
    try:
        return float(td.get("change_pct"))
    except Exception:
        return 0.0


def evidence_score(row):
    for key in ("evidence_score", "evidence", "score"):
        try:
            if row.get(key) is not None:
                return float(row[key])
        except Exception:
            pass
    return 0.0


@st.cache_data(ttl=60, show_spinner=False)
def live_reality(limit=15):
    return rank_candidates(limit=limit)


@st.cache_data(ttl=90, show_spinner=False)
def live_research(portfolio_json):
    portfolio = json.loads(portfolio_json)

    return research_candidates(
        fast_limit=50,
        research_limit=10,
        portfolio=portfolio,
    )


@st.cache_data(ttl=90, show_spinner=False)
def live_events(tickers):
    return get_market_events(tickers=list(tickers) if tickers else None)


def load_pipeline():
    path = Path(".eventpulse_pipeline.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def reset_test_account():
    """Reset the paper account to initial cash with ZERO positions.

    Qwen history and autonomous agent-cycle audit history are preserved.
    Trading/activity state is cleared for a clean autonomous demo.
    """
    initial_cash = float(get_initial_cash() or 0)

    conn = get_connection()

    try:
        conn.execute("DELETE FROM trades")
        conn.execute("DELETE FROM equity_snapshots")
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM theses")
        conn.commit()
    finally:
        conn.close()

    portfolio = {
        "cash": initial_cash,
        "positions": {},
    }

    save_portfolio(
        portfolio,
        equity=initial_cash,
    )

    return portfolio

def selected_research_row(rows, ticker):
    for row in rows:
        if row_ticker(row).upper() == ticker.upper():
            return row
    return None


def thesis_for(ticker):
    try:
        theses = get_open_theses()
    except Exception:
        return None

    for thesis in theses or []:
        try:
            if str(thesis[2]).upper() == ticker.upper():
                return thesis
        except Exception:
            pass
    return None




def render_qwen_news_interactive(
    selected_ticker=None,
    research_rows=None,
    reality_rows=None,
):
    """Deep interactive Qwen investment committee and event intelligence."""

    research_rows = research_rows or []
    reality_rows = reality_rows or []

    st.markdown(
        """
        <div class="ep-section-title">
            <span>QWEN INVESTMENT COUNCIL</span>
            <span class="ep-live-dot">● LIVE AUDIT</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # NORMALIZE SELECTED TICKER
    # --------------------------------------------------------

    selected = str(
        selected_ticker
        or st.session_state.get("selected_ticker")
        or ""
    ).upper()

    selected_underlying = selected

    if selected:
        try:
            selected_underlying = underlying_ticker(selected)
        except Exception:
            selected_underlying = (
                selected
                .lstrip("R")
                .replace("USDT", "")
            )

    # --------------------------------------------------------
    # FIND MARKET EVIDENCE
    # --------------------------------------------------------

    market_row = None

    for row in research_rows + reality_rows:
        ticker = str(
            row.get("ticker")
            or row.get("symbol")
            or row.get("execution_symbol")
            or ""
        ).upper()

        underlying = ticker

        try:
            underlying = underlying_ticker(ticker)
        except Exception:
            underlying = ticker.lstrip("R").replace("USDT", "")

        if ticker == selected or underlying == selected_underlying:
            market_row = row
            break

    # --------------------------------------------------------
    # LOAD PERSISTENT QWEN HISTORY
    # --------------------------------------------------------

    try:
        history = get_qwen_decision_history(
            limit=200,
            ticker=None,
        ) or []
    except Exception:
        history = []

    ticker_history = []

    for row in history:
        try:
            row_ticker = str(row[2]).upper()
        except Exception:
            continue

        if (
            row_ticker == selected
            or row_ticker == selected_underlying
        ):
            ticker_history.append(row)

    latest = ticker_history[0] if ticker_history else (
        history[0] if history else None
    )

    # --------------------------------------------------------
    # TOP COUNCIL STATUS
    # --------------------------------------------------------

    if latest:
        (
            qid,
            timestamp,
            q_ticker,
            decision,
            confidence,
            q_price,
            reasoning,
            catalyst,
            fundamental,
            valuation,
            market,
            bull,
            bear,
            invalidation,
            horizon,
        ) = latest

        q_ticker = str(q_ticker)

        decision = str(decision or "WAIT").upper()

        confidence_value = float(confidence or 0)

        price_value = q_price

        if market_row:
            price_value = (
                market_row.get("last_price")
                or market_row.get("price")
                or price_value
            )

        st.markdown(
            f"""
            <div class="ep-qwen-head">
                <div>
                    <div class="ep-qwen-ticker">{q_ticker}</div>
                    <div class="ep-qwen-time">
                        COUNCIL RUN · {timestamp}
                    </div>
                </div>
                <div class="ep-qwen-decision">{decision}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "CONFIDENCE",
            f"{confidence_value:.0%}",
        )

        c2.metric(
            "PRICE",
            (
                f"${float(price_value):,.2f}"
                if price_value is not None
                else "—"
            ),
        )

        move = None
        turnover = None
        spread = None
        evidence_score = None

        if market_row:
            move = (
                market_row.get("change_24h_pct")
                or market_row.get("change_pct")
            )

            turnover = (
                market_row.get("turnover_24h")
                or market_row.get("quote_volume")
                or market_row.get("turnover")
            )

            spread = (
                market_row.get("spread_pct")
                or market_row.get("spread")
            )

            evidence_score = market_row.get("evidence_score")

        c3.metric(
            "24H MOVE",
            (
                f"{float(move):+.2f}%"
                if move is not None
                else "—"
            ),
        )

        c4.metric(
            "EVIDENCE",
            (
                f"{float(evidence_score):.0f}"
                if evidence_score is not None
                else "—"
            ),
        )

        # ----------------------------------------------------
        # COUNCIL CONCLUSION
        # ----------------------------------------------------

        st.markdown("### COUNCIL CONCLUSION")

        st.info(
            reasoning
            or "No council reasoning was recorded."
        )

        # ----------------------------------------------------
        # MARKET CONTEXT
        # ----------------------------------------------------

        with st.expander(
            "MARKET CONTEXT",
            expanded=True,
        ):
            m1, m2, m3, m4 = st.columns(4)

            m1.metric(
                "REALITY PRICE",
                (
                    f"${float(price_value):,.2f}"
                    if price_value is not None
                    else "—"
                ),
            )

            m2.metric(
                "TURNOVER",
                (
                    f"${float(turnover):,.0f}"
                    if turnover is not None
                    else "—"
                ),
            )

            m3.metric(
                "SPREAD",
                (
                    f"{float(spread):.3f}%"
                    if spread is not None
                    else "—"
                ),
            )

            m4.metric(
                "HORIZON",
                horizon or "—",
            )

            if market:
                st.markdown("**MARKET THESIS**")
                st.write(market)

        # ----------------------------------------------------
        # EVENT / CATALYST
        # ----------------------------------------------------

        with st.expander(
            "EVENT & CATALYST",
            expanded=True,
        ):
            st.markdown("**TRIGGER**")
            st.write(catalyst or "No catalyst recorded.")

            selected_news = st.session_state.get("selected_news")

            if selected_news:
                headline = (
                    selected_news.get("headline")
                    or selected_news.get("title")
                    or ""
                )

                if headline:
                    st.markdown("**SOURCE HEADLINE**")
                    st.write(headline)

                source = (
                    selected_news.get("source")
                    or selected_news.get("publisher")
                )

                if source:
                    st.caption(f"Source: {source}")

        # ----------------------------------------------------
        # FUNDAMENTALS + VALUATION
        # ----------------------------------------------------

        left, right = st.columns(2)

        with left:
            with st.expander(
                "FUNDAMENTAL THESIS",
                expanded=True,
            ):
                st.write(
                    fundamental
                    or "No fundamental thesis recorded."
                )

        with right:
            with st.expander(
                "VALUATION THESIS",
                expanded=True,
            ):
                st.write(
                    valuation
                    or "No valuation thesis recorded."
                )

        # ----------------------------------------------------
        # SCENARIO ANALYSIS
        # ----------------------------------------------------

        st.markdown("### SCENARIO ANALYSIS")

        bull_col, bear_col = st.columns(2)

        with bull_col:
            with st.expander(
                "BULL CASE",
                expanded=True,
            ):
                st.write(
                    bull
                    or "No bull case recorded."
                )

        with bear_col:
            with st.expander(
                "BEAR CASE",
                expanded=True,
            ):
                st.write(
                    bear
                    or "No bear case recorded."
                )

        # ----------------------------------------------------
        # INVALIDATION
        # ----------------------------------------------------

        with st.expander(
            "THESIS INVALIDATION",
            expanded=True,
        ):
            st.warning(
                invalidation
                or "No invalidation condition recorded."
            )

        # ----------------------------------------------------
        # DECISION HISTORY
        # ----------------------------------------------------

        st.markdown("### DECISION HISTORY")

        if ticker_history:
            history_columns = st.columns(
                ["1.4fr", "0.7fr", "0.7fr", "1fr"]
            )

            history_columns[0].markdown("**TIME**")
            history_columns[1].markdown("**DECISION**")
            history_columns[2].markdown("**CONF.**")
            history_columns[3].markdown("**PRICE**")

            for row in ticker_history[:12]:
                try:
                    ts = row[1]
                    action = str(row[3]).upper()
                    conf = float(row[4] or 0)
                    px = row[5]
                except Exception:
                    continue

                cols = st.columns(
                    ["1.4fr", "0.7fr", "0.7fr", "1fr"]
                )

                cols[0].caption(str(ts))
                cols[1].markdown(f"**{action}**")
                cols[2].caption(f"{conf:.0%}")
                cols[3].caption(
                    f"${float(px):,.2f}"
                    if px is not None
                    else "—"
                )
        else:
            st.caption(
                "No previous Qwen decisions for this asset."
            )

        # ----------------------------------------------------
        # PORTFOLIO INTERPRETATION
        # ----------------------------------------------------

        with st.expander(
            "PORTFOLIO / POSITION LOGIC",
            expanded=False,
        ):
            position_weight = None

            if market_row:
                position_weight = (
                    market_row.get("position_weight")
                    or market_row.get("portfolio_position_weight")
                )

            if position_weight is not None:
                st.metric(
                    "CURRENT POSITION WEIGHT",
                    f"{float(position_weight):.1%}",
                )

            st.write(
                "Risk sizing and execution remain deterministic "
                "and separate from the Qwen investment judgment."
            )

    else:
        st.info(
            "No persistent Qwen decision is available yet. "
            "Run the autonomous council to populate the audit trail."
        )

        if history:
            st.markdown("### RECENT COUNCIL ACTIVITY")

            for idx, row in enumerate(history[:12]):
                try:
                    ticker = row[2]
                    decision = row[3]
                    confidence = float(row[4] or 0)
                    timestamp = row[1]
                except Exception:
                    continue

                if st.button(
                    f"{ticker}  ·  {decision}  ·  "
                    f"{confidence:.0%}  ·  {timestamp}",
                    key=f"qwen_recent_{idx}_{ticker}",
                    use_container_width=True,
                ):
                    st.session_state["selected_ticker"] = ticker
                    st.rerun()

    # --------------------------------------------------------
    # NEWS CHANNEL
    # --------------------------------------------------------

    st.markdown("---")
    st.markdown(
        """
        <div class="ep-section-title">
            <span>NEWS CHANNEL</span>
            <span class="ep-live-dot">● LIVE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    news_ticker = selected_underlying

    try:
        if news_ticker:
            news_rows = get_news(
                news_ticker,
                limit=10,
            ) or []
        else:
            news_rows = []
    except Exception:
        news_rows = []

    if not news_rows:
        try:
            event_rows = get_market_events(
                tickers=[news_ticker] if news_ticker else None
            ) or []
        except Exception:
            event_rows = []

        news_rows = event_rows

    if news_rows:
        for idx, item in enumerate(news_rows[:10]):
            headline = (
                item.get("headline")
                or item.get("title")
                or "Market event"
            )

            source = (
                item.get("source")
                or item.get("publisher")
                or "NEWS"
            )

            relevance = item.get("relevance")
            reason = (
                item.get("reason")
                or item.get("summary")
                or item.get("catalyst")
                or ""
            )

            ticker = (
                item.get("ticker")
                or news_ticker
                or ""
            )

            cols = st.columns([0.08, 0.68, 0.14, 0.10])

            with cols[0]:
                st.markdown("●")

            with cols[1]:
                if st.button(
                    headline[:100],
                    key=f"deep_news_{idx}_{ticker}",
                    use_container_width=True,
                ):
                    st.session_state["selected_news"] = item
                    st.session_state["selected_ticker"] = ticker
                    st.rerun()

                st.caption(
                    f"{source}"
                    + (
                        f" · relevance {float(relevance):.2f}"
                        if relevance is not None
                        else ""
                    )
                )

                if reason:
                    st.caption(reason)

            with cols[2]:
                st.caption(ticker)

            with cols[3]:
                if st.button(
                    "OPEN",
                    key=f"deep_news_open_{idx}_{ticker}",
                ):
                    st.session_state["selected_ticker"] = ticker
                    st.rerun()
    else:
        st.caption(
            "No actionable news currently returned by the event classifier."
        )



def qwen_decisions(pipeline):
    return (
        pipeline.get("qwen_decisions")
        or pipeline.get("qwen")
        or pipeline.get("decisions")
        or []
    )


def qwen_history():
    try:
        return get_qwen_decision_history(limit=100) or []
    except Exception:
        return []


def decision_for(decisions, ticker):
    for item in decisions:
        if not isinstance(item, dict):
            continue
        candidate = (
            item.get("ticker")
            or item.get("symbol")
            or item.get("underlying")
        )
        if candidate and str(candidate).upper() == ticker.upper():
            return item
    return None


# ============================================================
# STATE
# ============================================================

if "selected_asset" not in st.session_state:
    st.session_state.selected_asset = None

if "page" not in st.session_state:
    st.session_state.page = "Overview"


# ============================================================
# DATA LOAD
# ============================================================

portfolio = portfolio_dict()
pipeline = load_pipeline()

try:
    reality_rows = live_reality(15)
    reality_error = None
except Exception as exc:
    reality_rows = []
    reality_error = str(exc)

try:
    research_rows = live_research(
        json.dumps(
            portfolio,
            sort_keys=True,
            default=str,
        )
    )
    research_error = None
except Exception as exc:
    research_rows = []
    research_error = str(exc)

# The cache key above intentionally uses a hashable representation.
# Normalize to the same portfolio for any uncached direct calls.
if not research_rows and not research_error:
    try:
        research_rows = research_candidates(
            fast_limit=50,
            research_limit=10,
            portfolio=portfolio,
        )
    except Exception as exc:
        research_error = str(exc)

if reality_rows:
    tape_rows = reality_rows[:15]
else:
    tape_rows = research_rows[:15]

if st.session_state.selected_asset is None and tape_rows:
    st.session_state.selected_asset = row_ticker(tape_rows[0])

selected_ticker = st.session_state.selected_asset or ""


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown('<div class="ep-wordmark">EVENTPULSE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ep-sub">AUTONOMOUS EVENT-DRIVEN TRADING</div>',
        unsafe_allow_html=True,
    )

    nav = [
        "Overview",
        "Portfolio",
        "Events",
        "Qwen Council",
        "Risk",
        "Execution",
        "Thesis",
        "Agent Search",
    ]

    for item in nav:
        if st.button(
            item,
            key=f"nav_{item}",
            use_container_width=True,
        ):
            st.session_state.page = item
            st.rerun()

    st.markdown('<div class="ep-section">SYSTEM</div>', unsafe_allow_html=True)
    st.markdown('<div class="ep-status">US CASH CLOSED</div>', unsafe_allow_html=True)
    st.markdown('<div class="ep-status">rTOKEN LIVE</div>', unsafe_allow_html=True)
    st.markdown('<div class="ep-status">PAPER</div>', unsafe_allow_html=True)

    if st.button("KILL ARMED", key="kill_armed", use_container_width=True):
        st.warning("Kill switch is armed for paper execution. No live orders are enabled.")

    st.markdown('<div class="ep-section">PAPER CONTROL</div>', unsafe_allow_html=True)

    if st.button(
        "CLEAN SLATE — ZERO POSITIONS",
        key="reset_account",
        use_container_width=True,
    ):
        reset_test_account()
        st.cache_data.clear()
        st.session_state.selected_asset = None
        st.session_state.last_cycle_result = None
        st.success(
            "Clean slate restored. Initial cash available. "
            "Positions: 0. Agent ready."
        )
        st.rerun()


# ============================================================
# TOP BAR
# ============================================================

top_left, top_right = st.columns([2, 3])

with top_left:
    st.markdown('<div class="ep-title">Overview</div>', unsafe_allow_html=True)

with top_right:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(
        f'<div style="text-align:right;color:#7F8995;font:10px monospace;'
        f'letter-spacing:.06em;">LAST TICK {now} &nbsp;&nbsp; '
        f'US CASH CLOSED &nbsp;&nbsp; PAPER</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# KPI ROW
# ============================================================

equity = 100000.0
try:
    equity = float(portfolio["cash"])
    for pos in portfolio["positions"].values():
        if isinstance(pos, dict):
            equity += float(pos.get("quantity", 0)) * float(
                pos.get("average_price", 0)
            )
except Exception:
    pass

# Prefer pipeline's current equity when available.
for key in ("equity", "current_equity", "portfolio_equity"):
    try:
        if pipeline.get(key) is not None:
            equity = float(pipeline[key])
            break
    except Exception:
        pass

pnl = equity - 100000.0
pnl_pct = (pnl / 100000.0) * 100
positions_count = len(portfolio["positions"])

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f'<div class="ep-metric"><div class="ep-metric-label">EQUITY</div>'
        f'<div class="ep-metric-value">{money(equity)}</div>'
        f'<div>{pct(pnl_pct)}</div></div>',
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f'<div class="ep-metric"><div class="ep-metric-label">24H PNL</div>'
        f'<div class="ep-metric-value ep-negative">{money(pnl)}</div>'
        f'<span class="ep-live">LIVE</span></div>',
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f'<div class="ep-metric"><div class="ep-metric-label">CASH</div>'
        f'<div class="ep-metric-value">{money(portfolio["cash"])}</div>'
        f'<div class="ep-metric-caption">available capital</div></div>',
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        f'<div class="ep-metric"><div class="ep-metric-label">POSITIONS</div>'
        f'<div class="ep-metric-value">{positions_count}</div>'
        f'<div class="ep-metric-caption">book loaded</div></div>',
        unsafe_allow_html=True,
    )


# ============================================================
# PIPELINE
# ============================================================

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div class="ep-panel-title">AUTONOMOUS PIPELINE</div>',
    unsafe_allow_html=True,
)

# The dashboard is intentionally read-only here.
# It consumes the canonical cycle state instead of calling Qwen
# or reconstructing risk/execution itself.

cycle_result = st.session_state.get("eventpulse_cycle") or {}

reality_count = int(
    cycle_result.get("reality")
    or len(reality_rows)
    or 0
)

fast_count = int(
    cycle_result.get("fast")
    or 0
)

evidence_count = int(
    cycle_result.get("evidence")
    or len(research_rows)
    or 0
)

pipeline_decisions = (
    cycle_result.get("signals")
    or []
)

qwen_count = int(
    cycle_result.get("qwen")
    or len(pipeline_decisions)
    or 0
)

risk_count = int(
    cycle_result.get("risk")
    or 0
)

approved_count = int(
    cycle_result.get("approved")
    or 0
)

filled_count = int(
    cycle_result.get("filled")
    or (
        cycle_result.get("paper_execution", {})
        .get("filled", 0)
    )
    or 0
)

blocked_count = int(
    cycle_result.get("blocked")
    or 0
)

# Explicit paper-agent deployment.
# Deployment always uses the canonical event-driven cycle.
# Risk remains downstream and cannot be bypassed.

cycle_col, status_col = st.columns([1, 3])

with cycle_col:
    st.markdown(
        '<div class="ep-deploy">AUTONOMOUS PAPER AGENT</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "DEPLOY AGENT",
        key="deploy_eventpulse_agent",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner(
            "Deploying Reality → Evidence → Qwen → Risk → Paper..."
        ):
            result = execute_live_agent_cycle(
                execute_paper=True
            )

        st.session_state.eventpulse_cycle = result
        st.session_state.agent_deployed = True

        st.cache_data.clear()
        st.rerun()

    if st.session_state.get("agent_deployed"):
        st.markdown(
            '<div class="ep-deploy-status">● DEPLOYED · PAPER EXECUTION ENABLED</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="ep-deploy-status">○ OFFLINE · PAPER EXECUTION ARMED ON DEPLOY</div>',
            unsafe_allow_html=True,
        )

with status_col:
    cycle_error = cycle_result.get("error")

    if cycle_error:
        st.error(
            f"Cycle error: {cycle_error}"
        )
    elif cycle_result:
        st.caption(
            " · ".join([
                f"CYCLE {cycle_result.get('cycle_id', '—')}",
                f"REALITY {cycle_result.get('reality', 0)}",
                f"EVIDENCE {cycle_result.get('evidence', 0)}",
                f"QWEN {cycle_result.get('qwen', 0)}",
                f"APPROVED {cycle_result.get('approved', 0)}",
                f"FILLED {cycle_result.get('filled', 0)}",
                f"BLOCKED {cycle_result.get('blocked', 0)}",
                "PAPER ONLY",
            ])
        )
    else:
        st.caption(
            "Agent is offline. Deploying runs the canonical "
            "event-driven paper-trading cycle."
        )

stages = [
    ("REALITY", reality_count),
    ("FAST", fast_count),
    ("EVIDENCE", evidence_count),
    ("QWEN", qwen_count),
    ("RISK", risk_count),
    ("APPROVED", approved_count),
    ("FILLED", filled_count),
]

cols = st.columns(len(stages) * 2 - 1)

for i, (label, value) in enumerate(stages):
    with cols[i * 2]:
        st.markdown(
            f'<div class="ep-stage"><div class="ep-stage-label">{label}</div>'
            f'<div class="ep-stage-value">{value}</div></div>',
            unsafe_allow_html=True,
        )
    if i < len(stages) - 1:
        with cols[i * 2 + 1]:
            st.markdown('<div class="ep-arrow">→</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="ep-note" style="margin-top:10px;">'
    f'{reality_count} reality instruments → {fast_count} fast candidates → '
    f'{evidence_count} evidence finalists'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# REALITY TAPE
# ============================================================

if tape_rows:
    tape_items = []
    for row in tape_rows:
        ticker = row_ticker(row)
        price = row_price(row)
        change = row_change(row)
        cls = "ep-positive" if change >= 0 else "ep-negative"
        sign = "+" if change >= 0 else ""
        tape_items.append(
            f'<span class="ep-tape-item"><b>{ticker}</b> '
            f'${price:,.2f} '
            f'<span class="{cls}">{sign}{change:.2f}%</span></span>'
        )

    tape_html = "".join(tape_items * 2)
    st.markdown(
        f'<div class="ep-tape-wrap"><div class="ep-tape">{tape_html}</div></div>',
        unsafe_allow_html=True,
    )

options = [row_ticker(x) for x in tape_rows if row_ticker(x)]
if selected_ticker not in options and options:
    selected_ticker = options[0]
    st.session_state.selected_asset = selected_ticker

if options:
    chosen = st.selectbox(
        "ACTIVE REALITY ASSET",
        options,
        index=options.index(selected_ticker),
        key="active_asset_select",
    )
    if chosen != st.session_state.selected_asset:
        st.session_state.selected_asset = chosen
        st.rerun()


# ============================================================
# OVERVIEW / CORE TERMINAL
# ============================================================

if st.session_state.page == "Overview":

    left, middle, right = st.columns([1.1, 1.0, 1.35])

    # --------------------------------------------------------
    # MARKET INTELLIGENCE
    # --------------------------------------------------------
    with left:
        st.markdown(
            '<div class="ep-panel"><div class="ep-panel-title">'
            'MARKET INTELLIGENCE</div>'
            '<div class="ep-panel-sub">EVIDENCE-RANKED REALITY ASSETS</div>',
            unsafe_allow_html=True,
        )

        source_rows = research_rows if research_rows else reality_rows

        for row in source_rows[:15]:
            ticker = row_ticker(row)
            price = row_price(row)
            change = row_change(row)

            a, b = st.columns([5, 1])
            with a:
                if st.button(
                    f"{ticker}   ${price:,.2f}   {change:+.2f}%",
                    key=f"asset_{ticker}",
                    use_container_width=True,
                ):
                    st.session_state.selected_asset = ticker
                    st.rerun()

            with b:
                score = evidence_score(row)
                st.markdown(
                    f'<div class="ep-score">{score:.0f}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # EVENT BLOTTER
    # --------------------------------------------------------
    with middle:
        st.markdown(
            '<div class="ep-panel"><div class="ep-panel-title">'
            'EVENT BLOTTER</div>'
            '<div class="ep-panel-sub">LIVE EVENT FLOW</div>',
            unsafe_allow_html=True,
        )

        event_tickers = []

        for x in source_rows[:15]:
            symbol = row_ticker(x)

            try:
                event_tickers.append(underlying_ticker(symbol))
            except Exception:
                cleaned = str(symbol).upper()

                if cleaned.startswith("R"):
                    cleaned = cleaned[1:]

                if cleaned.endswith("USDT"):
                    cleaned = cleaned[:-4]

                event_tickers.append(cleaned)

        try:
            events = live_events(tuple(sorted(set(event_tickers))))
        except Exception as exc:
            events = []
            st.caption(f"News feed unavailable: {exc}")

        seen = set()

        for event in events or []:
            if not isinstance(event, dict):
                continue

            title = str(event.get("title") or "").strip()
            ticker = str(
                event.get("ticker")
                or event.get("symbol")
                or ""
            ).upper()

            key = (ticker, title)
            if not title or key in seen:
                continue
            seen.add(key)

            summary = (
                event.get("summary")
                or event.get("description")
                or "Event detected."
            )

            st.markdown(
                f'<div class="ep-row"><b>{ticker or "MARKET"}</b><br>'
                f'<span class="ep-small">{title[:100]}</span><br>'
                f'<span class="ep-small">{str(summary)[:140]}</span></div>',
                unsafe_allow_html=True,
            )

            if ticker and st.button(
                "OPEN",
                key=f"event_{len(seen)}",
                use_container_width=True,
            ):
                st.session_state.selected_asset = ticker
                st.rerun()

        if not seen:
            st.markdown(
                '<div class="ep-small">No actionable events currently '
                'returned by the news classifier.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # LIVE EVIDENCE
    # --------------------------------------------------------
    with right:
        st.markdown(
            '<div class="ep-panel ep-panel-tall"><div class="ep-panel-title">'
            'LIVE EVIDENCE</div>'
            f'<div class="ep-panel-sub">{selected_ticker}</div>',
            unsafe_allow_html=True,
        )

        selected = selected_research_row(research_rows, selected_ticker)
        if selected is None:
            selected = selected_research_row(reality_rows, selected_ticker)

        price = row_price(selected or {})
        move = row_change(selected or {})
        score = evidence_score(selected or {})

        st.markdown(
            f'<div style="font-size:30px;font-weight:700;">{money(price)}</div>'
            f'<div style="font-size:13px;margin:3px 0 18px;">'
            f'{pct(move)}</div>',
            unsafe_allow_html=True,
        )

        if selected:
            breakdown = selected.get("evidence_breakdown") or {}

            if isinstance(breakdown, dict) and breakdown:
                labels = []
                values = []

                for key, value in breakdown.items():
                    try:
                        values.append(float(value))
                        labels.append(str(key).replace("_", " ").upper())
                    except Exception:
                        pass

                if values:
                    evidence_df = pd.DataFrame(
                        {"Evidence": labels, "Score": values}
                    )
                    st.dataframe(
                        evidence_df,
                        hide_index=True,
                        use_container_width=True,
                    )

            st.markdown(
                f'<div class="ep-row">EVIDENCE SCORE '
                f'<span class="ep-score">{score:.1f}</span></div>',
                unsafe_allow_html=True,
            )

            td = selected.get("ticker_data") or {}
            turnover = (
                td.get("quote_volume")
                or selected.get("turnover")
                or selected.get("quote_volume")
            )
            bid = td.get("bid")
            ask = td.get("ask")

            spread = None
            try:
                if bid and ask:
                    mid = (float(bid) + float(ask)) / 2
                    spread = ((float(ask) - float(bid)) / mid) * 100
            except Exception:
                pass

            st.markdown(
                f'<div class="ep-row">TURNOVER '
                f'<b>{money(turnover) if turnover else "—"}</b></div>'
                f'<div class="ep-row">SPREAD '
                f'<b>{f"{spread:.3f}%" if spread is not None else "—"}</b></div>',
                unsafe_allow_html=True,
            )

        # Actual market history where available.
        try:
            history = get_market_data(selected_ticker)
            if history is not None:
                if isinstance(history, pd.DataFrame):
                    hist_df = history.copy()
                else:
                    hist_df = pd.DataFrame(history)

                numeric_cols = [
                    c for c in hist_df.columns
                    if c.lower() in {"close", "price", "last"}
                ]

                if numeric_cols:
                    st.line_chart(
                        hist_df[numeric_cols[0]],
                        height=170,
                    )
        except Exception:
            pass

        thesis = thesis_for(selected_ticker)

        if thesis:
            bull = thesis[7] if len(thesis) > 7 else None
            bear = thesis[8] if len(thesis) > 8 else None

            st.markdown("**BULL CASE**")
            st.caption(bull or "No bull case recorded.")

            st.markdown("**BEAR CASE**")
            st.caption(bear or "No bear case recorded.")

        if st.button(
            "OPEN THESIS",
            key="open_thesis",
            use_container_width=True,
        ):
            st.session_state.page = "Thesis"
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PORTFOLIO
# ============================================================

elif st.session_state.page == "Portfolio":
    from app.database import (
        get_latest_portfolio,
        get_initial_positions,
        get_trades,
    )

    st.title("Portfolio")
    st.caption(
        "PAPER BOOK · CAPITAL · POSITIONS · EXPOSURE"
    )

    portfolio = get_latest_portfolio() or {}
    positions = portfolio.get("positions", {}) or {}

    try:
        cash = float(
            portfolio.get("cash", 0.0) or 0.0
        )
    except Exception:
        cash = 0.0

    # ------------------------------------------------------------
    # CURRENT BOOK
    # ------------------------------------------------------------

    position_rows = []
    position_value = 0.0

    for ticker, position in positions.items():
        try:
            quantity = float(
                position.get("quantity", 0.0) or 0.0
            )
            average_price = float(
                position.get("average_price", 0.0) or 0.0
            )

            notional = quantity * average_price
            position_value += notional

            position_rows.append(
                {
                    "Asset": ticker,
                    "Quantity": quantity,
                    "Average price": average_price,
                    "Cost basis": notional,
                }
            )
        except Exception:
            continue

    equity = cash + position_value

    # ------------------------------------------------------------
    # TOP METRICS
    # ------------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Equity",
            f"${equity:,.2f}",
        )

    with c2:
        st.metric(
            "Cash",
            f"${cash:,.2f}",
        )

    with c3:
        st.metric(
            "Invested",
            f"${position_value:,.2f}",
        )

    with c4:
        st.metric(
            "Positions",
            f"{len(position_rows):,}",
        )

    st.divider()

    # ------------------------------------------------------------
    # CAPITAL ALLOCATION
    # ------------------------------------------------------------

    st.subheader("Capital Allocation")

    cash_weight = (
        cash / equity
        if equity > 0
        else 0.0
    )

    invested_weight = (
        position_value / equity
        if equity > 0
        else 0.0
    )

    a1, a2, a3 = st.columns(3)

    with a1:
        st.metric(
            "Cash allocation",
            f"{cash_weight:.1%}",
        )

    with a2:
        st.metric(
            "Invested allocation",
            f"{invested_weight:.1%}",
        )

    with a3:
        st.metric(
            "Book state",
            "LOADED",
        )

    # ------------------------------------------------------------
    # POSITION TABLE
    # ------------------------------------------------------------

    st.subheader("Open Positions")

    if position_rows:
        for row in position_rows:
            row["Weight"] = (
                row["Cost basis"] / equity
                if equity > 0
                else 0.0
            )

        position_rows.sort(
            key=lambda row: row["Cost basis"],
            reverse=True,
        )

        position_df = pd.DataFrame(
            position_rows
        )

        st.dataframe(
            position_df.style.format(
                {
                    "Quantity": "{:,.6f}",
                    "Average price": "${:,.2f}",
                    "Cost basis": "${:,.2f}",
                    "Weight": "{:.2%}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info(
            "No open positions."
        )

    # ------------------------------------------------------------
    # INITIAL BOOK
    # ------------------------------------------------------------

    st.divider()
    st.subheader("Initial Book")

    try:
        initial_positions = (
            get_initial_positions()
            or {}
        )
    except Exception:
        initial_positions = {}

    if isinstance(initial_positions, dict):
        initial_rows = []

        for ticker, position in initial_positions.items():
            if isinstance(position, dict):
                quantity = float(
                    position.get("quantity", 0.0) or 0.0
                )
                average_price = float(
                    position.get("average_price", 0.0) or 0.0
                )
            else:
                quantity = 0.0
                average_price = 0.0

            initial_rows.append(
                {
                    "Asset": ticker,
                    "Quantity": quantity,
                    "Average price": average_price,
                    "Cost basis": quantity * average_price,
                }
            )

        if initial_rows:
            initial_df = pd.DataFrame(
                initial_rows
            )

            st.dataframe(
                initial_df.style.format(
                    {
                        "Quantity": "{:,.6f}",
                        "Average price": "${:,.2f}",
                        "Cost basis": "${:,.2f}",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info(
                "No initial position snapshot recorded."
            )
    else:
        st.info(
            "No initial position snapshot recorded."
        )

    # ------------------------------------------------------------
    # TRADE ACTIVITY
    # ------------------------------------------------------------

    st.divider()
    st.subheader("Recent Portfolio Activity")

    try:
        trades = get_trades() or []
    except Exception:
        trades = []

    trade_rows = [
        trade
        for trade in reversed(trades)
        if isinstance(trade, dict)
    ][:10]

    if trade_rows:
        activity = []

        for trade in trade_rows:
            activity.append(
                {
                    "Timestamp": (
                        trade.get("timestamp")
                        or ""
                    ),
                    "Ticker": (
                        trade.get("research_ticker")
                        or trade.get("ticker")
                        or "—"
                    ),
                    "Side": str(
                        trade.get("side")
                        or "—"
                    ).upper(),
                    "Quantity": trade.get(
                        "quantity"
                    ),
                    "Price": trade.get(
                        "price"
                    ),
                    "Notional": trade.get(
                        "notional"
                    ),
                    "Status": str(
                        trade.get("status")
                        or "—"
                    ).upper(),
                }
            )

        activity_df = pd.DataFrame(
            activity
        )

        st.dataframe(
            activity_df.style.format(
                {
                    "Quantity": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"{float(value):,.6f}",
                    "Price": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"${float(value):,.2f}",
                    "Notional": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"${float(value):,.2f}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info(
            "No portfolio trades recorded yet."
        )

    # ------------------------------------------------------------
    # BOOK INTEGRITY
    # ------------------------------------------------------------

    st.divider()
    st.subheader("Book Integrity")

    i1, i2, i3 = st.columns(3)

    with i1:
        st.markdown("### Cash")
        st.write(
            "Tracked directly by the paper broker."
        )

    with i2:
        st.markdown("### Positions")
        st.write(
            "Maintained by executed paper fills."
        )

    with i3:
        st.markdown("### Equity")
        st.write(
            "Cash plus marked position cost basis."
        )

    st.caption(
        "Portfolio is read-only. Refreshing this page cannot place trades."
    )

# ============================================================
# EVENTS
# ============================================================

elif st.session_state.page == "Events":
    st.markdown(
        '<div class="ep-panel">'
        '<div class="ep-panel-title">EVENTS</div>'
        '<div class="ep-panel-sub">'
        'LIVE EVENT INTELLIGENCE · QWEN-READY CATALYST FLOW'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        events = live_events(tuple(options))
    except Exception as exc:
        events = []
        st.error(f"Event feed error: {exc}")

    events = [
        event for event in events
        if isinstance(event, dict)
    ]

    if not events:
        st.info("No actionable market events currently returned.")

    else:
        # --------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------

        total_events = len(events)

        high_relevance = sum(
            float(event.get("relevance", 0)) >= 0.75
            for event in events
        )

        positive_events = sum(
            str(event.get("catalyst", "")).lower() == "positive"
            for event in events
        )

        negative_events = sum(
            str(event.get("catalyst", "")).lower() == "negative"
            for event in events
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("EVENTS", total_events)

        with c2:
            st.metric("HIGH RELEVANCE", high_relevance)

        with c3:
            st.metric("POSITIVE", positive_events)

        with c4:
            st.metric("NEGATIVE", negative_events)

        st.divider()

        # --------------------------------------------------------
        # EVENT SELECTOR
        # --------------------------------------------------------

        labels = []

        for event in events:
            ticker = str(
                event.get("ticker") or "UNKNOWN"
            ).upper()

            headline = str(
                event.get("headline")
                or "Untitled event"
            ).strip()

            relevance = float(
                event.get("relevance", 0)
            )

            labels.append(
                f"{ticker} · {relevance:.0%} · {headline}"
            )

        selected_idx = st.selectbox(
            "SELECT EVENT",
            range(len(events)),
            format_func=lambda index: labels[index],
            key="selected_event_index",
        )

        selected_event = events[selected_idx]

        ticker = str(
            selected_event.get("ticker")
            or "UNKNOWN"
        ).upper()

        headline = str(
            selected_event.get("headline")
            or "Untitled event"
        ).strip()

        relevance = float(
            selected_event.get("relevance", 0)
        )

        catalyst = str(
            selected_event.get("catalyst")
            or "neutral"
        ).lower()

        reason = str(
            selected_event.get("reason")
            or "No classifier rationale available."
        ).strip()

        # --------------------------------------------------------
        # SELECTED EVENT
        # --------------------------------------------------------

        st.markdown("### Selected event")

        left, right = st.columns([4, 1])

        with left:
            st.markdown(f"**{ticker}**")
            st.markdown(f"#### {headline}")
            st.caption(reason)

        with right:
            st.metric("Relevance", f"{relevance:.0%}")
            st.caption(f"Catalyst: {catalyst.upper()}")

        # --------------------------------------------------------
        # QWEN HANDOFF
        # --------------------------------------------------------

        st.divider()
        st.markdown("### Event → Investment Council")

        handoff_left, handoff_right = st.columns([1, 3])

        with handoff_left:
            if st.button(
                "OPEN QWEN COUNCIL",
                key="open_qwen_from_event",
                use_container_width=True,
            ):
                st.session_state.selected_event_for_qwen = (
                    selected_event
                )
                st.session_state.page = "Qwen Council"
                st.rerun()

        with handoff_right:
            st.caption(
                f"{ticker} · {catalyst.upper()} · "
                f"{relevance:.0%} relevance · "
                "ready for evidence and Qwen evaluation"
            )

        # --------------------------------------------------------
        # EVENT STREAM
        # --------------------------------------------------------

        st.divider()
        st.markdown("### Actionable event stream")

        for index, event in enumerate(events):
            event_ticker = str(
                event.get("ticker") or "UNKNOWN"
            ).upper()

            event_headline = str(
                event.get("headline")
                or "Untitled event"
            ).strip()

            event_relevance = float(
                event.get("relevance", 0)
            )

            event_catalyst = str(
                event.get("catalyst")
                or "neutral"
            ).upper()

            event_reason = str(
                event.get("reason")
                or ""
            ).strip()

            with st.container(border=True):
                row_left, row_right = st.columns([5, 1])

                with row_left:
                    st.markdown(
                        f"**{event_ticker}**"
                    )
                    st.write(event_headline)

                    if event_reason:
                        st.caption(event_reason)

                with row_right:
                    st.metric(
                        "Relevance",
                        f"{event_relevance:.0%}",
                    )
                    st.caption(event_catalyst)

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# QWEN COUNCIL
# ============================================================

elif st.session_state.page == "Qwen Council":
    from app.database import get_qwen_decision_history

    st.title("Qwen Council")
    st.caption(
        "QWEN INVESTMENT COUNCIL · READ-ONLY DECISION AUDIT"
    )

    # ------------------------------------------------------------
    # LOAD CANONICAL QWEN HISTORY
    # ------------------------------------------------------------

    try:
        qwen_history = get_qwen_decision_history(
            limit=100
        )
    except Exception as exc:
        qwen_history = []
        st.error(
            f"Qwen history error: {exc}"
        )

    records = []

    for row in qwen_history or []:
        if isinstance(row, dict):
            records.append(dict(row))
            continue

        if not isinstance(row, (tuple, list)):
            continue

        # qwen_decisions:
        # id, timestamp, ticker, decision, confidence,
        # price, reasoning, catalyst,
        # fundamental_thesis, valuation_thesis,
        # market_thesis, bull_case, bear_case,
        # invalidation_condition, expected_horizon

        fields = [
            "id",
            "timestamp",
            "ticker",
            "decision",
            "confidence",
            "price",
            "reasoning",
            "catalyst",
            "fundamental_thesis",
            "valuation_thesis",
            "market_thesis",
            "bull_case",
            "bear_case",
            "invalidation_condition",
            "expected_horizon",
        ]

        record = {}

        for index, field in enumerate(fields):
            if index < len(row):
                record[field] = row[index]

        records.append(record)

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------

    buy_count = sum(
        str(record.get("decision", "")).upper()
        == "BUY"
        for record in records
    )

    sell_count = sum(
        str(record.get("decision", "")).upper()
        == "SELL"
        for record in records
    )

    wait_count = sum(
        str(record.get("decision", "")).upper()
        in {"WAIT", "HOLD"}
        for record in records
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Council decisions",
            len(records),
        )

    with c2:
        st.metric(
            "BUY",
            buy_count,
        )

    with c3:
        st.metric(
            "SELL",
            sell_count,
        )

    with c4:
        st.metric(
            "WAIT / HOLD",
            wait_count,
        )

    st.divider()

    if not records:
        st.info(
            "No Qwen decisions recorded yet. "
            "Run the canonical agent cycle from Overview."
        )
    else:
        # --------------------------------------------------------
        # DECISION SELECTOR
        # --------------------------------------------------------

        labels = []

        for index, record in enumerate(records):
            ticker = (
                record.get("ticker")
                or "UNKNOWN"
            )

            decision = (
                record.get("decision")
                or "—"
            )

            confidence = record.get(
                "confidence"
            )

            confidence_text = (
                "—"
                if confidence is None
                else f"{float(confidence):.0%}"
            )

            labels.append(
                f"{ticker} · "
                f"{str(decision).upper()} · "
                f"{confidence_text}"
            )

        selected_index = st.selectbox(
            "SELECT COUNCIL DECISION",
            range(len(labels)),
            format_func=lambda index:
                labels[index],
        )

        selected = records[
            selected_index
        ]

        ticker = (
            selected.get("ticker")
            or "UNKNOWN"
        )

        decision = (
            selected.get("decision")
            or "—"
        )

        confidence = selected.get(
            "confidence"
        )

        price = selected.get("price")

        # --------------------------------------------------------
        # DECISION HEADER
        # --------------------------------------------------------

        st.subheader(
            str(ticker).upper()
        )

        d1, d2, d3 = st.columns(3)

        with d1:
            st.metric(
                "Direction",
                str(decision).upper(),
            )

        with d2:
            st.metric(
                "Confidence",
                "—"
                if confidence is None
                else f"{float(confidence):.0%}",
            )

        with d3:
            st.metric(
                "Reference price",
                "—"
                if price is None
                else f"${float(price):,.2f}",
            )

        # --------------------------------------------------------
        # COUNCIL REASONING
        # --------------------------------------------------------

        st.divider()
        st.subheader("Council Reasoning")

        reasoning = (
            selected.get("reasoning")
            or ""
        )

        if reasoning:
            st.write(reasoning)
        else:
            st.caption(
                "No reasoning recorded."
            )

        catalyst = (
            selected.get("catalyst")
            or ""
        )

        if catalyst:
            st.subheader("Catalyst")
            st.write(catalyst)

        # --------------------------------------------------------
        # INVESTMENT CASE
        # --------------------------------------------------------

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("### Fundamental")
            value = (
                selected.get(
                    "fundamental_thesis"
                )
                or ""
            )
            st.write(
                value
                if value
                else "Not available."
            )

        with c2:
            st.markdown("### Valuation")
            value = (
                selected.get(
                    "valuation_thesis"
                )
                or ""
            )
            st.write(
                value
                if value
                else "Not available."
            )

        with c3:
            st.markdown("### Market")
            value = (
                selected.get(
                    "market_thesis"
                )
                or ""
            )
            st.write(
                value
                if value
                else "Not available."
            )

        # --------------------------------------------------------
        # BULL / BEAR
        # --------------------------------------------------------

        st.divider()

        b1, b2 = st.columns(2)

        with b1:
            st.subheader("Bull Case")
            value = (
                selected.get(
                    "bull_case"
                )
                or ""
            )
            st.write(
                value
                if value
                else "Not recorded."
            )

        with b2:
            st.subheader("Bear Case")
            value = (
                selected.get(
                    "bear_case"
                )
                or ""
            )
            st.write(
                value
                if value
                else "Not recorded."
            )

        # --------------------------------------------------------
        # INVALIDATION
        # --------------------------------------------------------

        st.subheader(
            "Invalidation Condition"
        )

        invalidation = (
            selected.get(
                "invalidation_condition"
            )
            or ""
        )

        if invalidation:
            st.warning(
                invalidation
            )
        else:
            st.caption(
                "No invalidation condition recorded."
            )

        horizon = (
            selected.get(
                "expected_horizon"
            )
            or ""
        )

        if horizon:
            st.subheader(
                "Expected Horizon"
            )
            st.write(horizon)

        # --------------------------------------------------------
        # DECISION HISTORY
        # --------------------------------------------------------

        st.divider()
        st.subheader(
            "Council Decision History"
        )

        history_rows = []

        for record in records:
            history_rows.append(
                {
                    "Timestamp": (
                        record.get(
                            "timestamp"
                        )
                        or ""
                    ),
                    "Ticker": (
                        record.get(
                            "ticker"
                        )
                        or "—"
                    ),
                    "Decision": (
                        record.get(
                            "decision"
                        )
                        or "—"
                    ),
                    "Confidence": record.get(
                        "confidence"
                    ),
                    "Price": record.get(
                        "price"
                    ),
                }
            )

        history_df = pd.DataFrame(
            history_rows
        )

        st.dataframe(
            history_df.style.format(
                {
                    "Confidence": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"{float(value):.0%}",
                    "Price": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"${float(value):,.2f}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

    st.caption(
        "Qwen Council is read-only. "
        "Decisions are generated by the canonical event-driven agent cycle."
    )

# ============================================================
# RISK
# ============================================================

elif st.session_state.page == "Risk":
    from app.database import (
        get_latest_portfolio,
        get_agent_cycle,
        get_trades,
    )
    from app.risk import (
        MIN_CONFIDENCE,
        MAX_TRADE_PORTFOLIO_PCT,
        MAX_POSITION_PCT,
        MAX_DAILY_LOSS_PCT,
        MAX_DRAWDOWN_PCT,
    )

    st.title("Risk")
    st.caption("DETERMINISTIC PYTHON RISK CONTROL · NO MODEL OVERRIDES")

    portfolio = get_latest_portfolio() or {}

    cash = float(portfolio.get("cash", 0.0) or 0.0)
    positions = portfolio.get("positions", {}) or {}

    # ------------------------------------------------------------
    # PORTFOLIO SNAPSHOT
    # ------------------------------------------------------------

    position_value = 0.0

    for ticker, position in positions.items():
        try:
            quantity = float(position.get("quantity", 0.0) or 0.0)
            average_price = float(position.get("average_price", 0.0) or 0.0)
            position_value += quantity * average_price
        except Exception:
            continue

    book_value = cash + position_value

    st.subheader("Portfolio Risk Snapshot")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Book value", f"${book_value:,.2f}")

    with c2:
        st.metric("Cash", f"${cash:,.2f}")

    with c3:
        st.metric("Position value", f"${position_value:,.2f}")

    with c4:
        st.metric("Open positions", str(len(positions)))

    # ------------------------------------------------------------
    # DETERMINISTIC LIMITS
    # ------------------------------------------------------------

    st.subheader("Deterministic Risk Limits")

    l1, l2, l3, l4, l5 = st.columns(5)

    with l1:
        st.metric(
            "Min confidence",
            f"{MIN_CONFIDENCE:.0%}",
        )

    with l2:
        st.metric(
            "Max trade",
            f"{MAX_TRADE_PORTFOLIO_PCT:.0%}",
        )

    with l3:
        st.metric(
            "Max position",
            f"{MAX_POSITION_PCT:.0%}",
        )

    with l4:
        st.metric(
            "Daily loss limit",
            f"{MAX_DAILY_LOSS_PCT:.0%}",
        )

    with l5:
        st.metric(
            "Max drawdown",
            f"{MAX_DRAWDOWN_PCT:.0%}",
        )

    st.info(
        "Qwen proposes direction and confidence. "
        "These deterministic Python controls decide whether a trade can proceed."
    )

    # ------------------------------------------------------------
    # CURRENT POSITION EXPOSURE
    # ------------------------------------------------------------

    st.subheader("Current Exposure")

    exposure_rows = []

    for ticker, position in positions.items():
        try:
            quantity = float(position.get("quantity", 0.0) or 0.0)
            average_price = float(position.get("average_price", 0.0) or 0.0)
            notional = quantity * average_price
            weight = (notional / book_value) if book_value > 0 else 0.0

            exposure_rows.append(
                {
                    "Asset": ticker,
                    "Quantity": quantity,
                    "Average price": average_price,
                    "Notional": notional,
                    "Portfolio weight": weight,
                    "Position limit": MAX_POSITION_PCT,
                    "Status": (
                        "WITHIN LIMIT"
                        if weight <= MAX_POSITION_PCT
                        else "LIMIT EXCEEDED"
                    ),
                }
            )
        except Exception:
            continue

    if exposure_rows:
        exposure_rows.sort(
            key=lambda row: row["Notional"],
            reverse=True,
        )

        exposure_df = pd.DataFrame(exposure_rows)

        st.dataframe(
            exposure_df.style.format(
                {
                    "Quantity": "{:.6f}",
                    "Average price": "${:,.2f}",
                    "Notional": "${:,.2f}",
                    "Portfolio weight": "{:.2%}",
                    "Position limit": "{:.0%}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No open positions in the current portfolio.")

    # ------------------------------------------------------------
    # LATEST AGENT RISK DECISIONS
    # ------------------------------------------------------------

    st.subheader("Latest Risk Decisions")

    try:
        cycle_rows = get_agent_cycle(limit=200)
    except Exception as exc:
        cycle_rows = []
        st.error(f"Risk audit error: {exc}")

    risk_rows = []

    if cycle_rows:
        for row in cycle_rows:
            # id, cycle_id, timestamp, stage, status,
            # ticker, decision, confidence, detail
            if len(row) < 9:
                continue

            stage = str(row[3] or "").upper()

            if stage != "RISK":
                continue

            risk_rows.append(
                {
                    "Timestamp": row[2],
                    "Ticker": row[5] or "—",
                    "Decision": row[6] or "—",
                    "Confidence": (
                        float(row[7])
                        if row[7] is not None
                        else None
                    ),
                    "Status": row[4] or "—",
                    "Reason": row[8] or "",
                }
            )

    if risk_rows:
        risk_df = pd.DataFrame(risk_rows)

        st.dataframe(
            risk_df.style.format(
                {
                    "Confidence": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"{float(value):.0%}"
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No risk decisions have been recorded yet.")

    # ------------------------------------------------------------
    # RISK GATE EXPLANATION
    # ------------------------------------------------------------

    st.subheader("Risk Gate")

    gate1, gate2, gate3 = st.columns(3)

    with gate1:
        st.markdown("### 01 · Direction")
        st.write(
            "HOLD and WAIT signals cannot create trades."
        )

    with gate2:
        st.markdown("### 02 · Confidence")
        st.write(
            f"BUY/SELL signals require at least {MIN_CONFIDENCE:.0%} confidence."
        )

    with gate3:
        st.markdown("### 03 · Portfolio")
        st.write(
            f"Trade size is capped at {MAX_TRADE_PORTFOLIO_PCT:.0%} "
            f"of portfolio value and individual positions at "
            f"{MAX_POSITION_PCT:.0%}."
        )

    # ------------------------------------------------------------
    # DAILY LOSS / DRAWDOWN SAFETY
    # ------------------------------------------------------------

    st.subheader("Account Protection")

    a1, a2 = st.columns(2)

    with a1:
        st.markdown("### Daily loss protection")
        st.write(
            f"Maximum permitted daily loss: {MAX_DAILY_LOSS_PCT:.0%}."
        )
        st.caption(
            "A breach prevents additional risk from being introduced."
        )

    with a2:
        st.markdown("### Drawdown protection")
        st.write(
            f"Maximum permitted portfolio drawdown: {MAX_DRAWDOWN_PCT:.0%}."
        )
        st.caption(
            "The deterministic risk layer remains authoritative over Qwen."
        )

    # ------------------------------------------------------------
    # RECENT FILLS / TRADE AUDIT
    # ------------------------------------------------------------

    st.subheader("Execution Audit")

    try:
        trades = get_trades()
    except Exception:
        trades = []

    if trades:
        trade_rows = []

        for trade in trades[-10:]:
            if isinstance(trade, dict):
                trade_rows.append(trade)

        if trade_rows:
            audit_df = pd.DataFrame(trade_rows)

            preferred_columns = [
                column
                for column in [
                    "timestamp",
                    "ticker",
                    "side",
                    "quantity",
                    "price",
                    "notional",
                    "status",
                ]
                if column in audit_df.columns
            ]

            if preferred_columns:
                st.dataframe(
                    audit_df[preferred_columns],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.dataframe(
                    audit_df,
                    hide_index=True,
                    use_container_width=True,
                )
        else:
            st.info("No recent paper executions recorded.")
    else:
        st.info("No paper executions recorded.")

    st.caption(
        "Risk is deterministic and auditable. "
        "Dashboard refreshes do not execute trades."
    )

# ============================================================
# EXECUTION
# ============================================================

elif st.session_state.page == "Execution":
    from app.database import (
        get_trades,
        get_agent_cycle,
    )

    st.title("Execution")
    st.caption(
        "PAPER EXECUTION · REALITY SYMBOL ROUTING · FULL ORDER AUDIT"
    )

    # ------------------------------------------------------------
    # TRADE HISTORY
    # ------------------------------------------------------------

    try:
        trades = get_trades()
    except Exception as exc:
        trades = []
        st.error(f"Execution history error: {exc}")

    trades = [
        trade for trade in (trades or [])
        if isinstance(trade, dict)
    ]

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------

    filled = [
        trade for trade in trades
        if str(trade.get("status", "")).upper() == "FILLED"
    ]

    failed = [
        trade for trade in trades
        if str(trade.get("status", "")).upper()
        in {"FAILED", "REJECTED", "BLOCKED"}
    ]

    total_notional = 0.0

    for trade in filled:
        try:
            total_notional += float(
                trade.get("notional", 0.0) or 0.0
            )
        except Exception:
            pass

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Recorded trades",
            f"{len(trades):,}",
        )

    with c2:
        st.metric(
            "Filled",
            f"{len(filled):,}",
        )

    with c3:
        st.metric(
            "Failed / rejected",
            f"{len(failed):,}",
        )

    with c4:
        st.metric(
            "Filled notional",
            f"${total_notional:,.2f}",
        )

    st.divider()

    # ------------------------------------------------------------
    # EXECUTION STATUS
    # ------------------------------------------------------------

    st.subheader("Execution Status")

    s1, s2, s3 = st.columns(3)

    with s1:
        st.markdown("### Broker")
        st.write("PaperBroker")

    with s2:
        st.markdown("### Mode")
        st.write("PAPER")

    with s3:
        st.markdown("### Live orders")
        st.write("DISABLED")

    st.info(
        "Dashboard refreshes are read-only. "
        "Paper orders are created only by the canonical event-driven agent cycle."
    )

    # ------------------------------------------------------------
    # ORDER LEDGER
    # ------------------------------------------------------------

    st.subheader("Order Ledger")

    if trades:
        rows = []

        for trade in reversed(trades):
            timestamp = (
                trade.get("timestamp")
                or trade.get("created_at")
                or ""
            )

            research_ticker = (
                trade.get("research_ticker")
                or trade.get("ticker")
                or "—"
            )

            execution_symbol = (
                trade.get("execution_symbol")
                or trade.get("ticker")
                or "—"
            )

            side = str(
                trade.get("side")
                or trade.get("action")
                or "—"
            ).upper()

            status = str(
                trade.get("status")
                or "—"
            ).upper()

            quantity = trade.get("quantity")
            price = trade.get("price")
            notional = trade.get("notional")

            rows.append(
                {
                    "Timestamp": timestamp,
                    "Research ticker": research_ticker,
                    "Execution symbol": execution_symbol,
                    "Side": side,
                    "Quantity": quantity,
                    "Price": price,
                    "Notional": notional,
                    "Status": status,
                }
            )

        ledger_df = pd.DataFrame(rows)

        st.dataframe(
            ledger_df.style.format(
                {
                    "Quantity": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"{float(value):,.6f}",
                    "Price": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"${float(value):,.2f}",
                    "Notional": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"${float(value):,.2f}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info(
            "No paper execution records yet."
        )

    # ------------------------------------------------------------
    # EXECUTION PIPELINE
    # ------------------------------------------------------------

    st.divider()
    st.subheader("Execution Pipeline")

    p1, p2, p3, p4, p5 = st.columns(5)

    with p1:
        st.markdown("### 01")
        st.write("Qwen signal")

    with p2:
        st.markdown("### 02")
        st.write("Python risk")

    with p3:
        st.markdown("### 03")
        st.write("Notional sizing")

    with p4:
        st.markdown("### 04")
        st.write("Reality symbol")

    with p5:
        st.markdown("### 05")
        st.write("Paper fill")

    st.caption(
        "Execution is downstream of deterministic risk approval."
    )

    # ------------------------------------------------------------
    # RECENT EXECUTION AUDIT
    # ------------------------------------------------------------

    st.divider()
    st.subheader("Agent Execution Audit")

    try:
        cycle_rows = get_agent_cycle(limit=200)
    except Exception:
        cycle_rows = []

    execution_audit = []

    for row in cycle_rows or []:
        if not isinstance(row, (tuple, list)):
            continue

        if len(row) < 9:
            continue

        # id, cycle_id, timestamp, stage, status,
        # ticker, decision, confidence, detail
        stage = str(row[3] or "").upper()

        if stage not in {
            "EXECUTION",
            "FILL",
            "PAPER",
            "RISK",
            "CYCLE",
        }:
            continue

        execution_audit.append(
            {
                "Timestamp": row[2],
                "Cycle": row[1],
                "Stage": stage,
                "Status": row[4] or "—",
                "Ticker": row[5] or "—",
                "Decision": row[6] or "—",
                "Confidence": row[7],
                "Detail": row[8] or "",
            }
        )

    if execution_audit:
        audit_df = pd.DataFrame(
            execution_audit
        )

        st.dataframe(
            audit_df.style.format(
                {
                    "Confidence": lambda value:
                        "—"
                        if pd.isna(value)
                        else f"{float(value):.0%}"
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info(
            "No execution-specific agent audit records yet."
        )

    # ------------------------------------------------------------
    # SAFETY NOTE
    # ------------------------------------------------------------

    st.divider()

    st.subheader("Execution Safety")

    st.write(
        "The dashboard does not execute trades. "
        "Only the canonical event-driven cycle can call PaperExecutor."
    )

    st.caption(
        "Paper mode only · no live broker orders · refresh-safe"
    )

# ============================================================
# THESIS
# ============================================================

elif st.session_state.page == "Thesis":
    from app.database import (
        get_open_theses,
        get_qwen_decision_history,
    )

    st.title("Thesis")
    st.caption(
        "INVESTMENT THESIS TRACKING · CATALYST → REASONING → INVALIDATION → OUTCOME"
    )

    # ------------------------------------------------------------
    # LOAD THESIS / QWEN HISTORY
    # ------------------------------------------------------------

    try:
        thesis_records = get_open_theses()
    except Exception:
        thesis_records = []

    try:
        qwen_records = get_qwen_decision_history(limit=100)
    except Exception:
        qwen_records = []

    # Normalize whatever the database returns into dictionaries.
    normalized = []

    for row in thesis_records or []:
        if isinstance(row, dict):
            normalized.append(dict(row))
        elif isinstance(row, (tuple, list)):
            # Best-effort support for legacy thesis rows.
            values = list(row)

            record = {}

            fields = [
                "id",
                "timestamp",
                "ticker",
                "thesis",
                "catalyst",
                "invalidation_condition",
                "expected_horizon",
                "status",
                "outcome",
            ]

            for index, field in enumerate(fields):
                if index < len(values):
                    record[field] = values[index]

            normalized.append(record)

    # Fall back to Qwen decisions if there are no dedicated thesis rows.
    if not normalized:
        for row in qwen_records or []:
            if isinstance(row, dict):
                normalized.append(dict(row))
            elif isinstance(row, (tuple, list)):
                values = list(row)

                # qwen_decisions:
                # id, timestamp, ticker, decision, confidence, price,
                # reasoning, catalyst, fundamental_thesis,
                # valuation_thesis, market_thesis, bull_case,
                # bear_case, invalidation_condition, expected_horizon

                record = {}

                fields = [
                    "id",
                    "timestamp",
                    "ticker",
                    "decision",
                    "confidence",
                    "price",
                    "reasoning",
                    "catalyst",
                    "fundamental_thesis",
                    "valuation_thesis",
                    "market_thesis",
                    "bull_case",
                    "bear_case",
                    "invalidation_condition",
                    "expected_horizon",
                ]

                for index, field in enumerate(fields):
                    if index < len(values):
                        record[field] = values[index]

                normalized.append(record)

    # Newest first.
    normalized = list(reversed(normalized))

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------

    total = len(normalized)

    buy_count = sum(
        str(row.get("decision", "")).upper() == "BUY"
        for row in normalized
    )

    sell_count = sum(
        str(row.get("decision", "")).upper() == "SELL"
        for row in normalized
    )

    wait_count = sum(
        str(row.get("decision", "")).upper() in {"WAIT", "HOLD"}
        for row in normalized
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Theses tracked", total)

    with c2:
        st.metric("BUY", buy_count)

    with c3:
        st.metric("SELL", sell_count)

    with c4:
        st.metric("WAIT / HOLD", wait_count)

    st.divider()

    # ------------------------------------------------------------
    # THESIS SELECTOR
    # ------------------------------------------------------------

    if not normalized:
        st.info(
            "No thesis records are available yet. "
            "Run an agent cycle to populate Qwen thesis history."
        )
    else:
        labels = []

        for index, row in enumerate(normalized):
            ticker = (
                row.get("ticker")
                or row.get("symbol")
                or "UNKNOWN"
            )

            decision = (
                row.get("decision")
                or row.get("direction")
                or "—"
            )

            timestamp = row.get("timestamp") or ""

            labels.append(
                f"{ticker} · {str(decision).upper()} · {timestamp}"
            )

        selected_index = st.selectbox(
            "SELECT THESIS",
            range(len(labels)),
            format_func=lambda index: labels[index],
        )

        selected = normalized[selected_index]

        ticker = (
            selected.get("ticker")
            or selected.get("symbol")
            or "UNKNOWN"
        )

        decision = (
            selected.get("decision")
            or selected.get("direction")
            or "—"
        )

        confidence = selected.get("confidence")

        price = selected.get("price")

        # --------------------------------------------------------
        # SELECTED THESIS
        # --------------------------------------------------------

        st.subheader(str(ticker).upper())

        top1, top2, top3, top4 = st.columns(4)

        with top1:
            st.metric(
                "Decision",
                str(decision).upper(),
            )

        with top2:
            if confidence is None:
                st.metric("Confidence", "—")
            else:
                st.metric(
                    "Confidence",
                    f"{float(confidence):.0%}",
                )

        with top3:
            if price is None:
                st.metric("Reference price", "—")
            else:
                st.metric(
                    "Reference price",
                    f"${float(price):,.2f}",
                )

        with top4:
            st.metric(
                "Status",
                str(
                    selected.get("status")
                    or "TRACKING"
                ).upper(),
            )

        st.divider()

        # --------------------------------------------------------
        # CATALYST
        # --------------------------------------------------------

        st.subheader("Catalyst")

        catalyst = selected.get("catalyst") or ""

        if catalyst:
            st.write(catalyst)
        else:
            st.caption("No catalyst recorded.")

        # --------------------------------------------------------
        # CORE THESIS
        # --------------------------------------------------------

        st.subheader("Core Thesis")

        reasoning = selected.get("reasoning") or selected.get("thesis") or ""

        if reasoning:
            st.write(reasoning)
        else:
            st.caption("No core reasoning recorded.")

        # --------------------------------------------------------
        # EVIDENCE BREAKDOWN
        # --------------------------------------------------------

        e1, e2, e3 = st.columns(3)

        with e1:
            st.markdown("### Fundamental")
            fundamental = (
                selected.get("fundamental_thesis")
                or selected.get("fundamental")
                or ""
            )

            if fundamental:
                st.write(fundamental)
            else:
                st.caption(
                    "No fundamental thesis recorded. "
                    "Qwen did not receive usable fundamental evidence."
                )

        with e2:
            st.markdown("### Valuation")
            valuation = (
                selected.get("valuation_thesis")
                or selected.get("valuation")
                or ""
            )

            if valuation:
                st.write(valuation)
            else:
                st.caption(
                    "No valuation thesis recorded. "
                    "Qwen did not receive usable valuation evidence."
                )

        with e3:
            st.markdown("### Market")
            market = selected.get("market_thesis") or ""
            st.write(
                market
                if market
                else "No market thesis recorded."
            )

        st.divider()

        # --------------------------------------------------------
        # BULL / BEAR
        # --------------------------------------------------------

        b1, b2 = st.columns(2)

        with b1:
            st.subheader("Bull Case")
            bull = selected.get("bull_case") or ""

            if bull:
                st.write(bull)
            else:
                st.caption("No bull case recorded.")

        with b2:
            st.subheader("Bear Case")
            bear = selected.get("bear_case") or ""

            if bear:
                st.write(bear)
            else:
                st.caption("No bear case recorded.")

        # --------------------------------------------------------
        # INVALIDATION
        # --------------------------------------------------------

        st.subheader("Invalidation Condition")

        invalidation = (
            selected.get("invalidation_condition")
            or ""
        )

        if invalidation:
            st.warning(invalidation)
        else:
            st.caption(
                "No explicit invalidation condition recorded."
            )

        # --------------------------------------------------------
        # HORIZON
        # --------------------------------------------------------

        horizon = selected.get("expected_horizon") or ""

        if horizon:
            st.subheader("Expected Horizon")
            st.write(horizon)

        # --------------------------------------------------------
        # THESIS HISTORY
        # --------------------------------------------------------

        st.divider()
        st.subheader("Thesis History")

        history_rows = []

        for row in normalized:
            history_rows.append(
                {
                    "Timestamp": row.get("timestamp") or "",
                    "Ticker": (
                        row.get("ticker")
                        or row.get("symbol")
                        or "—"
                    ),
                    "Decision": (
                        row.get("decision")
                        or row.get("direction")
                        or "—"
                    ),
                    "Confidence": row.get("confidence"),
                    "Price": row.get("price"),
                    "Status": (
                        row.get("status")
                        or "TRACKING"
                    ),
                }
            )

        history_df = pd.DataFrame(history_rows)

        if not history_df.empty:
            st.dataframe(
                history_df.style.format(
                    {
                        "Confidence": lambda value:
                            "—"
                            if pd.isna(value)
                            else f"{float(value):.0%}",
                        "Price": lambda value:
                            "—"
                            if pd.isna(value)
                            else f"${float(value):,.2f}",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )

    st.caption(
        "Thesis tracking is read-only. "
        "Trading decisions are created by the canonical agent cycle."
    )

# ============================================================
# AGENT SEARCH
# ============================================================

elif st.session_state.page == "Agent Search":
    from app.bitget_universe import (
        get_universe_symbols,
        underlying_ticker,
    )
    from app.universe_research import research_candidates

    st.title("Agent Search")
    st.caption(
        "REALITY UNIVERSE SEARCH · EVIDENCE-FIRST ASSET INSPECTION"
    )

    # ------------------------------------------------------------
    # SEARCH CONTROLS
    # ------------------------------------------------------------

    st.subheader("Search Reality Universe")

    query = st.text_input(
        "SEARCH ASSET",
        placeholder="Ticker or Reality symbol, e.g. NVDA or rNVDA",
    ).strip().upper()

    refresh = st.button(
        "REFRESH REALITY UNIVERSE",
        type="secondary",
    )

    if refresh:
        try:
            get_universe_symbols(force_refresh=True)
            st.success("Reality universe refreshed.")
        except Exception as exc:
            st.error(f"Reality refresh failed: {exc}")

    # ------------------------------------------------------------
    # LOAD UNIVERSE
    # ------------------------------------------------------------

    try:
        universe = get_universe_symbols(
            force_refresh=False
        )
    except Exception as exc:
        universe = []
        st.error(f"Reality universe error: {exc}")

    universe = list(universe or [])

    # ------------------------------------------------------------
    # FILTER
    # ------------------------------------------------------------

    if query:
        matches = []

        for symbol in universe:
            raw = str(symbol).upper()

            try:
                base = str(
                    underlying_ticker(raw)
                ).upper()
            except Exception:
                base = raw

            if (
                query in raw
                or query in base
            ):
                matches.append(
                    {
                        "Reality symbol": raw,
                        "Underlying": base,
                    }
                )

        matches = matches[:50]
    else:
        matches = [
            {
                "Reality symbol": str(symbol).upper(),
                "Underlying": str(symbol).upper(),
            }
            for symbol in universe[:50]
        ]

    # ------------------------------------------------------------
    # UNIVERSE SUMMARY
    # ------------------------------------------------------------

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Reality instruments",
            f"{len(universe):,}",
        )

    with c2:
        st.metric(
            "Search matches",
            f"{len(matches):,}",
        )

    with c3:
        st.metric(
            "Search status",
            "LIVE",
        )

    # ------------------------------------------------------------
    # SEARCH RESULTS
    # ------------------------------------------------------------

    if not matches:
        st.info(
            "No Reality instruments matched the search."
        )
    else:
        st.subheader("Matches")

        match_df = pd.DataFrame(matches)

        st.dataframe(
            match_df,
            hide_index=True,
            use_container_width=True,
        )

        options = [
            row["Reality symbol"]
            for row in matches
        ]

        selected_symbol = st.selectbox(
            "SELECT ASSET",
            options,
        )

        selected_underlying = next(
            (
                row["Underlying"]
                for row in matches
                if row["Reality symbol"] == selected_symbol
            ),
            selected_symbol,
        )

        st.divider()

        # --------------------------------------------------------
        # SELECTED ASSET
        # --------------------------------------------------------

        st.subheader(
            f"{selected_underlying} · {selected_symbol}"
        )

        st.caption(
            "Reality execution symbol and canonical underlying asset"
        )

        # --------------------------------------------------------
        # EVIDENCE LOOKUP
        # --------------------------------------------------------

        if st.button(
            "LOAD EVIDENCE",
            type="primary",
        ):
            try:
                evidence = research_candidates(
                    fast_limit=50,
                    research_limit=10,
                    portfolio=None,
                )

                selected_evidence = []

                for row in evidence or []:
                    if not isinstance(row, dict):
                        continue

                    symbol = str(
                        row.get("symbol")
                        or ""
                    ).upper()

                    underlying = str(
                        row.get("underlying")
                        or ""
                    ).upper()

                    if (
                        symbol == selected_symbol
                        or underlying == selected_underlying
                    ):
                        selected_evidence.append(row)

                if selected_evidence:
                    st.session_state[
                        "agent_search_evidence"
                    ] = selected_evidence[0]
                else:
                    st.session_state[
                        "agent_search_evidence"
                    ] = None

            except Exception as exc:
                st.session_state[
                    "agent_search_evidence"
                ] = None

                st.error(
                    f"Evidence lookup failed: {exc}"
                )

        evidence = st.session_state.get(
            "agent_search_evidence"
        )

        # --------------------------------------------------------
        # EVIDENCE PANEL
        # --------------------------------------------------------

        if evidence:
            st.divider()
            st.subheader("Evidence")

            ticker_data = (
                evidence.get("ticker_data")
                or {}
            )

            price = ticker_data.get("last")
            change = ticker_data.get("change_pct")
            turnover = ticker_data.get(
                "quote_volume"
            )
            bid = ticker_data.get("bid")
            ask = ticker_data.get("ask")

            e1, e2, e3, e4 = st.columns(4)

            with e1:
                st.metric(
                    "Last",
                    "—"
                    if price is None
                    else f"${float(price):,.2f}",
                )

            with e2:
                st.metric(
                    "24H move",
                    "—"
                    if change is None
                    else f"{float(change):+.2f}%",
                )

            with e3:
                st.metric(
                    "Turnover",
                    "—"
                    if turnover is None
                    else f"${float(turnover):,.0f}",
                )

            with e4:
                if bid is not None and ask is not None:
                    spread = (
                        (float(ask) - float(bid))
                        / float(ask)
                        * 100
                        if float(ask) != 0
                        else 0
                    )
                    spread_text = f"{spread:.3f}%"
                else:
                    spread_text = "—"

                st.metric(
                    "Spread",
                    spread_text,
                )

            st.subheader("Evidence Score")

            score = evidence.get(
                "evidence_score"
            )

            fast_score = evidence.get(
                "score"
            )

            s1, s2, s3 = st.columns(3)

            with s1:
                st.metric(
                    "Evidence score",
                    "—"
                    if score is None
                    else f"{float(score):.1f}",
                )

            with s2:
                st.metric(
                    "Fast score",
                    "—"
                    if fast_score is None
                    else f"{float(fast_score):.1f}",
                )

            with s3:
                st.metric(
                    "Reality status",
                    str(
                        evidence.get("status")
                        or "UNKNOWN"
                    ).upper(),
                )

            breakdown = (
                evidence.get(
                    "evidence_breakdown"
                )
                or {}
            )

            if breakdown:
                st.subheader(
                    "Evidence Breakdown"
                )

                breakdown_rows = [
                    {
                        "Factor": str(key).replace(
                            "_",
                            " ",
                        ).title(),
                        "Score": value,
                    }
                    for key, value in breakdown.items()
                ]

                st.dataframe(
                    pd.DataFrame(breakdown_rows),
                    hide_index=True,
                    use_container_width=True,
                )

            # ----------------------------------------------------
            # NAVIGATION
            # ----------------------------------------------------

            st.divider()

            n1, n2 = st.columns(2)

            with n1:
                if st.button(
                    "OPEN QWEN COUNCIL",
                    use_container_width=True,
                ):
                    st.session_state[
                        "selected_asset_for_qwen"
                    ] = selected_underlying

                    st.session_state.page = (
                        "Qwen Council"
                    )

                    st.rerun()

            with n2:
                if st.button(
                    "OPEN THESIS",
                    use_container_width=True,
                ):
                    st.session_state[
                        "selected_asset_for_thesis"
                    ] = selected_underlying

                    st.session_state.page = (
                        "Thesis"
                    )

                    st.rerun()

        else:
            st.info(
                "Select an asset and press LOAD EVIDENCE "
                "to inspect its live evidence pack."
            )

    st.caption(
        "Agent Search is read-only. "
        "It does not create signals or execute trades."
    )

