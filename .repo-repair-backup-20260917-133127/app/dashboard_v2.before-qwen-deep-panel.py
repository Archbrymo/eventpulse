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
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

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
    initial_cash = float(get_initial_cash() or 0)
    initial_positions = get_initial_positions() or {}

    positions = {}
    for symbol, data in initial_positions.items():
        if isinstance(data, dict):
            positions[symbol] = {
                "quantity": float(data.get("quantity", 0)),
                "average_price": float(data.get("average_price", 0)),
            }
        elif isinstance(data, (tuple, list)):
            positions[symbol] = {
                "quantity": float(data[0]),
                "average_price": float(data[1]),
            }

    # Preserve initial account definition while clearing test activity.
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
        "positions": positions,
    }
    save_portfolio(portfolio, equity=100000.0)
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
    """Interactive Qwen Council + live news channel."""

    research_rows = research_rows or []
    reality_rows = reality_rows or []

    st.markdown(
        """
        <div class="ep-section-title">
            <span>INTELLIGENCE CHANNEL</span>
            <span class="ep-live-dot">● LIVE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 1], gap="large")

    # --------------------------------------------------------
    # NEWS CHANNEL
    # --------------------------------------------------------
    with left:
        st.markdown("### NEWS CHANNEL")
        st.caption("Live event-driven headlines mapped to Reality assets.")

        news_ticker = selected_ticker or ""

        try:
            if news_ticker:
                clean = str(news_ticker).upper()
                try:
                    clean = underlying_ticker(clean)
                except Exception:
                    clean = clean.lstrip("R").replace("USDT", "")

                news_rows = get_news(clean, limit=8) or []
            else:
                news_rows = []
        except Exception:
            news_rows = []

        if news_rows:
            for idx, item in enumerate(news_rows[:8]):
                headline = (
                    item.get("headline")
                    or item.get("title")
                    or "Untitled market event"
                )
                source = item.get("source") or item.get("publisher") or "NEWS"
                relevance = item.get("relevance")
                catalyst = item.get("catalyst") or item.get("reason") or ""

                label = f"{headline[:72]}"
                if st.button(
                    f"◉ {label}",
                    key=f"news_select_{idx}_{clean}",
                    use_container_width=True,
                ):
                    st.session_state["selected_news"] = item
                    st.session_state["selected_news_ticker"] = clean
                    st.rerun()

                meta = f"{source}"
                if relevance is not None:
                    try:
                        meta += f"  •  relevance {float(relevance):.2f}"
                    except Exception:
                        pass

                st.caption(meta)

                if catalyst:
                    st.markdown(
                        f"<div class='ep-news-reason'>{catalyst}</div>",
                        unsafe_allow_html=True,
                    )
        else:
            # Fall back to market events so the channel doesn't silently
            # appear broken when ticker-specific headlines are unavailable.
            try:
                event_rows = get_market_events(
                    tickers=[selected_ticker] if selected_ticker else None
                ) or []
            except Exception:
                event_rows = []

            if event_rows:
                for idx, event in enumerate(event_rows[:8]):
                    headline = (
                        event.get("headline")
                        or event.get("title")
                        or "Market event"
                    )
                    ticker = event.get("ticker") or ""
                    relevance = event.get("relevance")

                    if st.button(
                        f"◉ {headline[:72]}",
                        key=f"event_news_{idx}_{ticker}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_news"] = event
                        st.session_state["selected_news_ticker"] = ticker
                        st.rerun()

                    caption = ticker
                    if relevance is not None:
                        try:
                            caption += f"  •  relevance {float(relevance):.2f}"
                        except Exception:
                            pass
                    st.caption(caption)
            else:
                st.info(
                    "No actionable headlines currently returned by the news classifier."
                )

    # --------------------------------------------------------
    # QWEN COUNCIL
    # --------------------------------------------------------
    with right:
        st.markdown("### QWEN COUNCIL")

        try:
            history = get_qwen_decision_history(
                limit=100,
                ticker=None,
            ) or []
        except Exception:
            history = []

        selected_qwen = None

        if selected_ticker:
            normalized = str(selected_ticker).upper()
            for row in history:
                try:
                    if str(row[2]).upper() == normalized:
                        selected_qwen = row
                        break
                except Exception:
                    continue

            if selected_qwen is None:
                try:
                    clean = underlying_ticker(normalized)
                except Exception:
                    clean = normalized.lstrip("R").replace("USDT", "")

                for row in history:
                    try:
                        if str(row[2]).upper() == clean:
                            selected_qwen = row
                            break
                    except Exception:
                        continue

        if selected_qwen:
            # qwen_decisions schema:
            # id,timestamp,ticker,decision,confidence,price,
            # reasoning,catalyst,fundamental,valuation,market,
            # bull,bear,invalidation,horizon
            (
                qid,
                timestamp,
                ticker,
                decision,
                confidence,
                price,
                reasoning,
                catalyst,
                fundamental,
                valuation,
                market,
                bull,
                bear,
                invalidation,
                horizon,
            ) = selected_qwen

            st.markdown(
                f"""
                <div class="ep-qwen-head">
                    <div>
                        <div class="ep-qwen-ticker">{ticker}</div>
                        <div class="ep-qwen-time">{timestamp}</div>
                    </div>
                    <div class="ep-qwen-decision">{decision}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("CONFIDENCE", f"{float(confidence or 0):.0%}")
            c2.metric(
                "PRICE",
                f"${float(price):,.2f}" if price is not None else "—",
            )
            c3.metric("HORIZON", horizon or "—")

            st.markdown("**COUNCIL REASONING**")
            st.write(reasoning or "No reasoning recorded.")

            st.markdown("**CATALYST**")
            st.write(catalyst or "No catalyst recorded.")

            a, b = st.columns(2)

            with a:
                st.markdown("**BULL CASE**")
                st.write(bull or "Not recorded.")

                st.markdown("**FUNDAMENTAL THESIS**")
                st.write(fundamental or "Not recorded.")

                st.markdown("**MARKET THESIS**")
                st.write(market or "Not recorded.")

            with b:
                st.markdown("**BEAR CASE**")
                st.write(bear or "Not recorded.")

                st.markdown("**VALUATION THESIS**")
                st.write(valuation or "Not recorded.")

                st.markdown("**INVALIDATION**")
                st.write(invalidation or "Not recorded.")

        elif history:
            st.caption(
                "No historical Qwen decision is recorded for the selected asset."
            )

            recent = history[:6]

            for idx, row in enumerate(recent):
                try:
                    ticker = row[2]
                    decision = row[3]
                    confidence = row[4]
                    timestamp = row[1]
                except Exception:
                    continue

                if st.button(
                    f"{ticker}  ·  {decision}  ·  "
                    f"{float(confidence or 0):.0%}",
                    key=f"qwen_history_select_{idx}_{ticker}",
                    use_container_width=True,
                ):
                    st.session_state["selected_ticker"] = ticker
                    st.rerun()
        else:
            st.info(
                "No persistent Qwen decisions recorded yet. "
                "Run the autonomous council to populate the audit trail."
            )

    # --------------------------------------------------------
    # SELECTED NEWS DETAIL
    # --------------------------------------------------------
    selected_news = st.session_state.get("selected_news")

    if selected_news:
        st.markdown("---")
        st.markdown("### SELECTED EVENT")

        headline = (
            selected_news.get("headline")
            or selected_news.get("title")
            or "Market event"
        )

        st.markdown(f"**{headline}**")

        event_ticker = (
            selected_news.get("ticker")
            or st.session_state.get("selected_news_ticker")
            or ""
        )

        if event_ticker:
            st.caption(f"Asset: {event_ticker}")

        reason = (
            selected_news.get("reason")
            or selected_news.get("summary")
            or selected_news.get("catalyst")
        )

        if reason:
            st.write(reason)

        if st.button(
            "OPEN LIVE EVIDENCE",
            key="open_selected_news_evidence",
        ):
            st.session_state["selected_ticker"] = event_ticker
            st.rerun()

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


def persist_pipeline_qwen_decisions(decisions):
    """
    Persist pipeline Qwen decisions once they appear.
    Avoid duplicate entries when Streamlit reruns.
    """
    if not decisions:
        return

    history = qwen_history()

    recent_keys = set()

    for row in history:
        try:
            # id, timestamp, ticker, decision, confidence, price, ...
            ticker = str(row[2]).upper()
            action = str(row[3]).upper()
            price = row[5]
            recent_keys.add(
                (
                    ticker,
                    action,
                    round(float(price), 4) if price is not None else None,
                )
            )
        except Exception:
            continue

    for item in decisions:
        if not isinstance(item, dict):
            continue

        ticker = (
            item.get("ticker")
            or item.get("symbol")
            or item.get("underlying")
        )

        if not ticker:
            continue

        ticker = str(ticker).upper()

        action = (
            item.get("decision")
            or item.get("action")
            or item.get("signal")
            or "WAIT"
        )

        action = str(action).upper()

        if action not in {"BUY", "SELL", "HOLD", "WAIT"}:
            continue

        confidence = item.get("confidence")
        price = (
            item.get("price")
            or item.get("current_price")
            or item.get("entry_price")
        )

        try:
            price_key = round(float(price), 4) if price is not None else None
        except Exception:
            price_key = None

        key = (ticker, action, price_key)

        if key in recent_keys:
            continue

        try:
            save_qwen_decision(
                ticker=ticker,
                decision=action,
                confidence=confidence,
                price=price,
                reasoning=item.get("reasoning", ""),
                catalyst=item.get("catalyst", ""),
                fundamental_thesis=item.get("fundamental_thesis", ""),
                valuation_thesis=item.get("valuation_thesis", ""),
                market_thesis=item.get("market_thesis", ""),
                bull_case=item.get("bull_case", ""),
                bear_case=item.get("bear_case", ""),
                invalidation_condition=item.get(
                    "invalidation_condition", ""
                ),
                expected_horizon=item.get("expected_horizon", ""),
            )
            recent_keys.add(key)
        except Exception:
            pass


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

    st.markdown('<div class="ep-section">TEST ACCOUNT</div>', unsafe_allow_html=True)

    if st.button(
        "RESET TEST ACCOUNT → $100,000",
        key="reset_account",
        use_container_width=True,
    ):
        reset_test_account()
        st.cache_data.clear()
        st.session_state.selected_asset = None
        st.success("Paper test account restored to the initial $100,000 state.")
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

reality_count = 0
try:
    reality_count = int(universe_summary().get("count", 0))
except Exception:
    reality_count = len(reality_rows)

fast_count = int(
    pipeline.get("fast_count")
    or pipeline.get("fast_candidates_count")
    or 50
)

evidence_count = int(
    pipeline.get("evidence_count")
    or pipeline.get("research_count")
    or len(research_rows)
    or 10
)

pipeline_decisions = qwen_decisions(pipeline)

# Persist any Qwen decisions present in the pipeline.
persist_pipeline_qwen_decisions(pipeline_decisions)

history_rows = qwen_history()

qwen_count = len(pipeline_decisions)

# If the pipeline snapshot has no current decisions, show
# the latest distinct Qwen decisions from the persistent history.
if qwen_count == 0:
    seen_qwen = set()

    for row in history_rows:
        try:
            key = (str(row[2]).upper(), str(row[3]).upper())
            if key not in seen_qwen:
                seen_qwen.add(key)
                qwen_count += 1
        except Exception:
            pass

risk = pipeline.get("risk") or {}
risk_approved = pipeline.get("risk_approved")
approved_count = int(
    pipeline.get("approved_count")
    or (1 if risk_approved is True else 0)
)
filled_count = int(
    pipeline.get("filled_count")
    or pipeline.get("paper_filled")
    or 0
)

stages = [
    ("REALITY", reality_count),
    ("FAST", fast_count),
    ("EVIDENCE", evidence_count),
    ("QWEN", qwen_count),
    ("RISK", approved_count),
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
    st.markdown(
        '<div class="ep-panel"><div class="ep-panel-title">PORTFOLIO</div>'
        '<div class="ep-panel-sub">PAPER BOOK</div>',
        unsafe_allow_html=True,
    )

    rows = []
    for symbol, position in portfolio["positions"].items():
        if isinstance(position, dict):
            qty = position.get("quantity", 0)
            avg = position.get("average_price", 0)
        else:
            qty, avg = position

        rows.append(
            {
                "Asset": symbol,
                "Quantity": qty,
                "Average Price": avg,
                "Notional": float(qty) * float(avg),
            }
        )

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No positions in the paper book.")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# EVENTS
# ============================================================

elif st.session_state.page == "Events":
    st.markdown(
        '<div class="ep-panel"><div class="ep-panel-title">EVENTS</div>'
        '<div class="ep-panel-sub">NEWS AND CATALYST FLOW</div>',
        unsafe_allow_html=True,
    )

    try:
        events = live_events(tuple(options))
    except Exception as exc:
        events = []
        st.error(f"Event feed error: {exc}")

    if events:
        event_rows = []
        for event in events:
            if isinstance(event, dict):
                event_rows.append(
                    {
                        "Ticker": event.get("ticker") or event.get("symbol"),
                        "Title": event.get("title"),
                        "Summary": event.get("summary"),
                        "Relevance": event.get("relevance"),
                        "Sentiment": event.get("sentiment"),
                    }
                )
        st.dataframe(
            pd.DataFrame(event_rows),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No actionable market events currently returned.")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# QWEN COUNCIL
# ============================================================

elif st.session_state.page == "Qwen Council":
    st.markdown(
        '<div class="ep-panel"><div class="ep-panel-title">QWEN COUNCIL</div>'
        '<div class="ep-panel-sub">EVIDENCE → QWEN → DECISION</div>',
        unsafe_allow_html=True,
    )

    decisions = qwen_decisions(pipeline)

    # Persist current pipeline decisions.
    persist_pipeline_qwen_decisions(decisions)

    history = qwen_history()

    # --------------------------------------------------------
    # CURRENT COUNCIL
    # --------------------------------------------------------
    st.markdown(
        '<div class="ep-panel-title" style="margin-top:14px;">'
        'CURRENT COUNCIL</div>',
        unsafe_allow_html=True,
    )

    if decisions:
        for decision in decisions:
            if not isinstance(decision, dict):
                continue

            ticker = (
                decision.get("ticker")
                or decision.get("symbol")
                or decision.get("underlying")
                or "UNKNOWN"
            )

            action = (
                decision.get("decision")
                or decision.get("action")
                or decision.get("signal")
                or "WAIT"
            )

            confidence = decision.get("confidence")
            price = (
                decision.get("price")
                or decision.get("current_price")
            )

            st.markdown(
                f'<div class="ep-row">'
                f'<b>{ticker}</b> &nbsp; '
                f'<span class="ep-live">{str(action).upper()}</span> '
                f'&nbsp; CONFIDENCE '
                f'{confidence if confidence is not None else "—"}'
                f' &nbsp; PRICE '
                f'{money(price) if price is not None else "—"}'
                f'</div>',
                unsafe_allow_html=True,
            )

            reasoning = decision.get("reasoning")
            if reasoning:
                st.caption(reasoning)

            for label, key in [
                ("FUNDAMENTAL THESIS", "fundamental_thesis"),
                ("VALUATION THESIS", "valuation_thesis"),
                ("MARKET THESIS", "market_thesis"),
                ("BULL CASE", "bull_case"),
                ("BEAR CASE", "bear_case"),
                ("INVALIDATION", "invalidation_condition"),
            ]:
                value = decision.get(key)
                if value:
                    st.markdown(f"**{label}**")
                    st.caption(value)

    else:
        st.info("No current Qwen decision in the latest pipeline run.")

    # --------------------------------------------------------
    # DECISION HISTORY
    # --------------------------------------------------------
    st.markdown(
        '<div class="ep-panel-title" style="margin-top:24px;">'
        'DECISION HISTORY</div>'
        '<div class="ep-panel-sub">'
        'PREVIOUS BUY / SELL / HOLD / WAIT DECISIONS'
        '</div>',
        unsafe_allow_html=True,
    )

    if history:
        rows = []

        for row in history:
            try:
                rows.append(
                    {
                        "Time": row[1],
                        "Ticker": row[2],
                        "Decision": str(row[3]).upper(),
                        "Confidence": row[4],
                        "Price": row[5],
                        "Reasoning": row[6],
                    }
                )
            except Exception:
                continue

        if rows:
            st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                use_container_width=True,
            )

            st.markdown(
                '<div class="ep-small" style="margin-top:8px;">'
                'Persistent SQLite audit trail. Includes BUY, SELL, HOLD and WAIT.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("No persistent Qwen decisions recorded yet.")
    else:
        st.info("No persistent Qwen decisions recorded yet.")

    # --------------------------------------------------------
    # TRADING DECISION HISTORY
    # --------------------------------------------------------
    trades = get_trades() or []

    if trades:
        st.markdown(
            '<div class="ep-panel-title" style="margin-top:24px;">'
            'EXECUTION HISTORY</div>'
            '<div class="ep-panel-sub">'
            'PAPER BUY / SELL ACTIVITY'
            '</div>',
            unsafe_allow_html=True,
        )

        execution_rows = []

        for trade in trades:
            try:
                execution_rows.append(
                    {
                        "Time": trade[1],
                        "Ticker": trade[2],
                        "Decision": str(trade[3]).upper(),
                        "Quantity": trade[4],
                        "Price": trade[5],
                        "Reasoning": trade[8] if len(trade) > 8 else "",
                    }
                )
            except Exception:
                continue

        if execution_rows:
            st.dataframe(
                pd.DataFrame(execution_rows),
                hide_index=True,
                use_container_width=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# RISK
# ============================================================

elif st.session_state.page == "Risk":
    st.markdown(
        '<div class="ep-panel"><div class="ep-panel-title">RISK</div>'
        '<div class="ep-panel-sub">DETERMINISTIC PYTHON GATE</div>',
        unsafe_allow_html=True,
    )

    risk_obj = pipeline.get("risk") or {}

    fields = [
        ("Approved", pipeline.get("approved_count")),
        ("Blocked", pipeline.get("blocked_count")),
        ("Daily loss", risk_obj.get("daily_loss_pct")),
        ("Drawdown", risk_obj.get("drawdown_pct")),
        ("Reason", risk_obj.get("reason")),
    ]

    for label, value in fields:
        st.markdown(
            f'<div class="ep-row"><span class="ep-muted">{label}</span>'
            f'<br><b>{value if value is not None else "—"}</b></div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# EXECUTION
# ============================================================

elif st.session_state.page == "Execution":
    st.markdown(
        '<div class="ep-panel"><div class="ep-panel-title">EXECUTION</div>'
        '<div class="ep-panel-sub">PAPER EXECUTOR</div>',
        unsafe_allow_html=True,
    )

    trades = get_trades() or []

    if trades:
        df = pd.DataFrame(
            trades,
            columns=[
                "id",
                "timestamp",
                "ticker",
                "side",
                "quantity",
                "price",
                "value",
                "confidence",
                "reasoning",
            ],
        )
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No paper executions recorded.")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# THESIS
# ============================================================

elif st.session_state.page == "Thesis":
    st.markdown(
        '<div class="ep-panel"><div class="ep-panel-title">THESIS</div>'
        '<div class="ep-panel-sub">HORIZON-AWARE THESIS TRACKING</div>',
        unsafe_allow_html=True,
    )

    theses = get_open_theses() or []

    if theses:
        thesis_columns = [
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
        ]

        df = pd.DataFrame(theses, columns=thesis_columns)

        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No open theses.")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# AGENT SEARCH
# ============================================================

elif st.session_state.page == "Agent Search":
    st.markdown(
        '<div class="ep-panel"><div class="ep-panel-title">AGENT SEARCH</div>'
        '<div class="ep-panel-sub">TICKER · EVENT · THESIS · TRADE REASONING</div>',
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "SEARCH",
        placeholder="Search ticker, event, thesis, or trade reasoning…",
        label_visibility="collapsed",
    )

    q = query.strip().lower()

    if q:
        matches = []

        for row in reality_rows + research_rows:
            ticker = row_ticker(row)
            text = json.dumps(row, default=str).lower()
            if q in text or q in ticker.lower():
                matches.append(
                    (
                        "ASSET",
                        ticker,
                        row.get("reasoning") or row.get("thesis") or "",
                    )
                )

        for thesis in get_open_theses() or []:
            text = " ".join(map(str, thesis)).lower()
            if q in text:
                matches.append(
                    ("THESIS", str(thesis[2]), str(thesis[5]))
                )

        for trade in get_trades() or []:
            text = " ".join(map(str, trade)).lower()
            if q in text:
                matches.append(
                    ("TRADE", str(trade[2]), str(trade[-1]))
                )

        if matches:
            seen = set()
            for kind, ticker, detail in matches[:20]:
                key = (kind, ticker)
                if key in seen:
                    continue
                seen.add(key)

                st.markdown(
                    f'<div class="ep-row"><b>{kind}</b> '
                    f'{ticker}<br><span class="ep-small">'
                    f'{detail[:220]}</span></div>',
                    unsafe_allow_html=True,
                )

                if kind == "ASSET" and ticker:
                    if st.button(
                        f"OPEN {ticker}",
                        key=f"search_{kind}_{ticker}",
                    ):
                        st.session_state.selected_asset = ticker
                        st.session_state.page = "Overview"
                        st.rerun()
        else:
            st.info("No matching records.")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# DIAGNOSTICS
# ============================================================

if reality_error:
    st.caption(f"Reality feed warning: {reality_error}")

if research_error:
    st.caption(f"Research feed warning: {research_error}")

st.markdown(
    '<div style="text-align:center;color:#4D5660;font-size:9px;'
    'letter-spacing:.1em;margin-top:25px;">'
    'EVENTPULSE · AUTONOMOUS EVENT-DRIVEN TRADING · PAPER MODE'
    '</div>',
    unsafe_allow_html=True,
)
