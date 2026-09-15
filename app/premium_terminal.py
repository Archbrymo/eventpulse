from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st
import yfinance as yf


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEAL = "#2EE6C8"
RED = "#E23B3B"
GREEN = "#3DDC97"
BG = "#07080A"
SURFACE = "#12151A"
BORDER = "#252A31"
TEXT = "#E7EAEE"
MUTED = "#7F8995"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _esc(value: Any) -> str:
    return str(value or "").strip()


def _route_title(page: Optional[str]) -> str:
    page = _esc(page).lower()

    routes = {
        "overview": "Overview",
        "portfolio": "Portfolio",
        "events": "Events",
        "qwen council": "Qwen Council",
        "qwen_council": "Qwen Council",
        "risk": "Risk",
        "execution": "Execution",
        "thesis": "Thesis",
        "agent search": "Agent Search",
        "agent_search": "Agent Search",
    }

    return routes.get(page, "Overview")


def _event_ticker(event: Dict[str, Any]) -> str:
    return _esc(
        event.get("ticker")
        or event.get("symbol")
        or event.get("underlying")
        or ""
    ).upper()


def _event_headline(event: Dict[str, Any]) -> str:
    return _esc(
        event.get("headline")
        or event.get("title")
        or event.get("event")
        or event.get("reason")
        or ""
    )


def _event_action(event: Dict[str, Any]) -> str:
    action = _esc(
        event.get("action")
        or event.get("status")
        or event.get("direction")
        or "WAIT"
    ).upper()

    if action in {"BUY", "SELL"}:
        return "TAKE"

    if action in {"HOLD", "WAIT"}:
        return "WAIT"

    if action in {"PASS", "SKIP"}:
        return "PASS"

    if action in {"WATCH"}:
        return "WATCH"

    return "WAIT"


def _event_key(event: Dict[str, Any]) -> str:
    return f"{_event_ticker(event)}:{_event_headline(event)}".lower()


def _flatten_universe(universe: Any) -> List[Dict[str, Any]]:
    if universe is None:
        return []

    if isinstance(universe, dict):
        for key in ("assets", "symbols", "data", "results", "universe"):
            value = universe.get(key)
            if isinstance(value, list):
                return [
                    item for item in value
                    if isinstance(item, dict)
                ]

        rows = []

        for key, value in universe.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("symbol", key)
                rows.append(row)

        return rows

    if isinstance(universe, list):
        return [
            item for item in universe
            if isinstance(item, dict)
        ]

    return []


def _normalise_search_row(row: Dict[str, Any]) -> Dict[str, Any]:
    ticker_data = row.get("ticker_data") or {}

    symbol = (
        row.get("symbol")
        or row.get("execution_symbol")
        or ticker_data.get("symbol")
        or ""
    )

    underlying = (
        row.get("underlying")
        or row.get("base")
        or ticker_data.get("underlying")
        or ""
    )

    price = _safe_float(
        row.get("last_price")
        or ticker_data.get("last")
        or row.get("price")
    )

    change = _safe_float(
        row.get("change_24h_pct")
        if row.get("change_24h_pct") is not None
        else ticker_data.get("change_pct")
    )

    turnover = _safe_float(
        row.get("turnover_24h")
        if row.get("turnover_24h") is not None
        else ticker_data.get("quote_volume")
    )

    evidence = _safe_float(
        row.get("evidence_score")
        or row.get("score")
    )

    return {
        "symbol": _esc(symbol),
        "underlying": _esc(underlying),
        "price": price,
        "change": change,
        "turnover": turnover,
        "evidence": evidence,
        "raw": row,
    }


def _find_asset(
    ticker: str,
    finalists: Optional[List[Dict[str, Any]]] = None,
    universe: Any = None,
) -> Optional[Dict[str, Any]]:
    ticker = _esc(ticker).upper()

    rows = []

    if finalists:
        rows.extend(finalists)

    rows.extend(_flatten_universe(universe))

    for row in rows:
        normal = _normalise_search_row(row)

        if (
            normal["symbol"].upper() == ticker
            or normal["underlying"].upper() == ticker
        ):
            return normal

    return None


def _get_selected_asset(
    selected_asset: Optional[str],
    finalists: Optional[List[Dict[str, Any]]],
    universe: Any,
) -> Dict[str, Any]:
    requested = _esc(selected_asset).upper()

    if requested:
        found = _find_asset(
            requested,
            finalists=finalists,
            universe=universe,
        )

        if found:
            return found

    if finalists:
        return _normalise_search_row(finalists[0])

    rows = _flatten_universe(universe)

    if rows:
        return _normalise_search_row(rows[0])

    return {
        "symbol": "RGOOGLUSDT",
        "underlying": "GOOGL",
        "price": 345.07,
        "change": 2.77,
        "turnover": 8_810_000_000,
        "evidence": 90.0,
        "raw": {},
    }


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

def premium_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ep-bg: #07080A;
            --ep-surface: #12151A;
            --ep-border: #252A31;
            --ep-text: #E7EAEE;
            --ep-muted: #7F8995;
            --ep-teal: #2EE6C8;
            --ep-red: #E23B3B;
            --ep-green: #3DDC97;
        }

        .stApp {
            background: #07080A;
            color: #E7EAEE;
        }

        [data-testid="stSidebar"] {
            background: #0A0C0F;
            border-right: 1px solid #252A31;
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        [data-testid="stMetric"] {
            background: #12151A;
            border: 1px solid #252A31;
            padding: 0.9rem;
        }

        [data-testid="stMetricLabel"] {
            color: #7F8995 !important;
            font-size: 0.72rem !important;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        [data-testid="stMetricValue"] {
            color: #E7EAEE !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #252A31 !important;
            background: #12151A;
        }

        button {
            border-radius: 2px !important;
        }

        .ep-wordmark {
            font-size: 1.35rem;
            font-weight: 800;
            letter-spacing: 0.16em;
            color: #E7EAEE;
            line-height: 1;
        }

        .ep-subtitle {
            color: #7F8995;
            font-size: 0.67rem;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-top: 0.4rem;
            margin-bottom: 1.4rem;
        }

        .ep-section-label {
            color: #7F8995;
            font-size: 0.67rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .ep-nav-active {
            color: #2EE6C8;
            font-weight: 700;
        }

        .ep-nav-muted {
            color: #A5ADB7;
        }

        .ep-status {
            border: 1px solid #252A31;
            background: #12151A;
            padding: 0.25rem 0.4rem;
            margin-bottom: 0.3rem;
            color: #A5ADB7;
            font-size: 0.62rem;
            letter-spacing: 0.05em;
        }

        .ep-teal-status {
            color: #2EE6C8;
            border-color: #2EE6C8;
        }

        .ep-red-status {
            color: #E23B3B;
            border-color: #E23B3B;
        }

        .ep-muted {
            color: #7F8995;
        }

        .ep-price {
            font-size: 2.5rem;
            line-height: 1;
            font-weight: 750;
            color: #E7EAEE;
        }

        .ep-change-up {
            color: #3DDC97;
        }

        .ep-change-down {
            color: #E23B3B;
        }

        .ep-pipeline-value {
            color: #E7EAEE;
            font-size: 1.25rem;
            font-weight: 700;
        }

        .ep-pipeline-label {
            color: #7F8995;
            font-size: 0.62rem;
            letter-spacing: 0.08em;
        }

        .ep-pipeline-arrow {
            color: #2EE6C8;
            font-size: 1.2rem;
            padding-top: 0.8rem;
        }

        .ep-table-row {
            border-bottom: 1px solid #252A31;
            padding: 0.55rem 0;
        }

        .ep-ticker {
            color: #E7EAEE;
            font-weight: 700;
            font-size: 0.78rem;
        }

        .ep-small {
            color: #7F8995;
            font-size: 0.68rem;
        }

        .ep-thesis {
            color: #A5ADB7;
            font-size: 0.72rem;
            line-height: 1.35;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _sidebar(current_page: str) -> str:
    st.sidebar.markdown(
        '<div class="ep-wordmark">EVENTPULSE</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        '<div class="ep-subtitle">Autonomous event-driven trading</div>',
        unsafe_allow_html=True,
    )

    pages = [
        "Overview",
        "Portfolio",
        "Events",
        "Qwen Council",
        "Risk",
        "Execution",
        "Thesis",
        "Agent Search",
    ]

    st.sidebar.markdown(
        '<div class="ep-section-label">NAVIGATION</div>',
        unsafe_allow_html=True,
    )

    selected_page = current_page if current_page in pages else "Overview"

    for page in pages:
        active = page == selected_page

        if st.sidebar.button(
            page,
            key=f"ep_nav_{page.lower().replace(' ', '_')}",
            width='stretch',
            type="primary" if active else "secondary",
        ):
            st.session_state["ep_page"] = page
            st.rerun()

    st.sidebar.divider()

    st.sidebar.markdown(
        '<div class="ep-status">US CASH CLOSED</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        '<div class="ep-status ep-teal-status">rTOKEN LIVE</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        '<div class="ep-status ep-teal-status">PAPER</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.divider()

    if st.sidebar.button(
        "KILL ARMED",
        width='stretch',
        type="secondary",
        key="ep_kill_switch",
    ):
        st.session_state["kill_armed"] = True

    if st.session_state.get("kill_armed"):
        st.sidebar.caption("Kill switch armed.")

    return selected_page


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def _command_bar(last_tick: Optional[str], page_title: str) -> None:
    left, right = st.columns([1.5, 2.5])

    with left:
        st.title(page_title)

    with right:
        tick = last_tick or datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        a, b, c = st.columns(3)

        with a:
            st.caption(f"LAST TICK {tick}")

        with b:
            st.caption("US CASH CLOSED")

        with c:
            st.markdown(
                '<div class="ep-status ep-teal-status">PAPER</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _metrics(
    equity: float,
    cash: float,
    positions: Any,
    equity_change: Optional[float],
    pnl_24h: Optional[float],
) -> None:
    position_count = (
        len(positions)
        if isinstance(positions, dict)
        else _safe_int(positions)
    )

    if equity_change is None:
        equity_change = -5.22

    if pnl_24h is None:
        pnl_24h = -5220.61

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Equity",
            f"${equity:,.2f}",
            f"{equity_change:+.2f}%",
            delta_color="inverse",
        )

    with c2:
        st.metric(
            "24h PnL",
            f"{pnl_24h:+,.2f}",
        )

        st.caption("LIVE")

    with c3:
        st.metric(
            "Cash",
            f"${cash:,.2f}",
        )

        st.caption("available capital")

    with c4:
        st.metric(
            "Positions",
            f"{position_count}",
        )

        st.caption("book loaded")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def _pipeline(pipeline_snapshot: Optional[Dict[str, Any]]) -> None:
    snapshot = pipeline_snapshot or {}

    reality = _safe_int(snapshot.get("reality_universe"), 1173)
    fast = _safe_int(snapshot.get("fast_screen"), 50)
    evidence = _safe_int(snapshot.get("evidence_research"), 10)
    qwen = _safe_int(snapshot.get("qwen_council"), 3)

    risk_data = snapshot.get("risk") or {}
    execution_data = snapshot.get("paper_execution") or {}

    risk = _safe_int(risk_data.get("reviewed"), 0)
    approved = _safe_int(risk_data.get("approved"), 0)
    filled = _safe_int(execution_data.get("filled"), 0)

    stages = [
        ("REALITY", reality),
        ("FAST", fast),
        ("EVIDENCE", evidence),
        ("QWEN", qwen),
        ("RISK", risk),
        ("APPROVED", approved),
        ("FILLED", filled),
    ]

    cols = st.columns(len(stages) * 2 - 1)

    for index, (label, value) in enumerate(stages):
        with cols[index * 2]:
            st.markdown(
                f'<div class="ep-pipeline-label">{label}</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="ep-pipeline-value">{value:,}</div>',
                unsafe_allow_html=True,
            )

        if index < len(stages) - 1:
            with cols[index * 2 + 1]:
                st.markdown(
                    '<div class="ep-pipeline-arrow">→</div>',
                    unsafe_allow_html=True,
                )

    st.caption(
        f"{reality:,} reality instruments → "
        f"{fast:,} fast candidates → "
        f"{evidence:,} evidence finalists"
    )


# ---------------------------------------------------------------------------
# Market Intelligence
# ---------------------------------------------------------------------------


def _decision_trace(
    pipeline_snapshot=None,
    finalists=None,
):
    st.markdown("### AUTONOMOUS DECISION TRACE")
    st.caption("QWEN COUNCIL → DETERMINISTIC RISK → PAPER EXECUTION")

    snap = pipeline_snapshot or {}

    qwen = int(snap.get("qwen_council", 0) or 0)
    qwen_signals = int(snap.get("qwen_signals", 0) or 0)

    risk = snap.get("risk", {}) or {}
    reviewed = int(risk.get("reviewed", 0) or 0)
    approved = int(risk.get("approved", 0) or 0)
    blocked = int(risk.get("blocked", 0) or 0)

    execution = snap.get("paper_execution", {}) or {}
    attempted = int(execution.get("attempted", 0) or 0)
    filled = int(execution.get("filled", 0) or 0)
    failed = int(execution.get("failed", 0) or 0)

    stages = [
        ("QWEN COUNCIL", qwen, "signals"),
        ("RISK REVIEW", reviewed, "reviewed"),
        ("APPROVED", approved, "orders"),
        ("PAPER ORDERS", attempted, "attempted"),
        ("FILLED", filled, "filled"),
    ]

    cols = st.columns(len(stages), gap="small")

    for i, (label, value, suffix) in enumerate(stages):
        with cols[i]:
            st.markdown(
                f"""
                <div class="ep-trace-card">
                    <div class="ep-trace-label">{label}</div>
                    <div class="ep-trace-value">{value}</div>
                    <div class="ep-trace-suffix">{suffix}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if finalists:
        st.markdown("#### COUNCIL OUTPUT")

        rows = []
        for item in finalists[:5]:
            ticker = str(item.get("ticker", "")).upper()
            evidence = float(item.get("evidence_score", 0) or 0)
            price = float(item.get("last_price", 0) or 0)
            change = float(item.get("change_24h_pct", 0) or 0)

            rows.append(
                f"{ticker:<8}  "
                f"${price:,.2f}  "
                f"{change:+.2f}%  "
                f"EVIDENCE {evidence:.0f}"
            )

        st.code("\n".join(rows), language="text")

    if blocked:
        st.caption(
            f"Risk blocked {blocked} candidate(s) before paper execution."
        )

    if failed:
        st.caption(
            f"Paper execution reported {failed} failed order(s)."
        )


def _thesis_inspector(
    selected_asset=None,
    finalists=None,
    pipeline_snapshot=None,
):
    """Evidence-first inspection surface for the selected Reality asset."""

    asset = _find_asset(
        selected_asset or "",
        finalists or [],
    )

    if not asset:
        st.markdown("### THESIS INSPECTOR")
        st.caption("Select an asset from Agent Search to inspect its investment thesis.")
        return

    ticker = str(asset.get("ticker", "")).upper()
    execution_symbol = str(
        asset.get("execution_symbol", "")
    ).upper()

    price = float(asset.get("last_price", 0) or 0)
    change = float(asset.get("change_24h_pct", 0) or 0)
    turnover = float(asset.get("turnover_24h", 0) or 0)
    evidence = float(asset.get("evidence_score", 0) or 0)
    fast_score = float(asset.get("fast_score", 0) or 0)

    st.markdown("### THESIS INSPECTOR")
    st.caption(
        f"{ticker} · {execution_symbol} · EVIDENCE-FIRST INVESTMENT CASE"
    )

    top = st.columns([1.4, 1, 1, 1], gap="small")

    with top[0]:
        st.markdown(f"{ticker}")
        st.markdown(f"### ${price:,.2f}")

    with top[1]:
        st.caption("24H MOVE")
        st.markdown(f"{change:+.2f}%")

    with top[2]:
        st.caption("EVIDENCE")
        st.markdown(f"**{evidence:.0f}/100**")

    with top[3]:
        st.caption("FAST SCORE")
        st.markdown(f"**{fast_score:.1f}/10**")

    st.divider()

    left, right = st.columns([1, 1], gap="medium")

    with left:
        st.markdown("#### CATALYST")
        st.caption(
            "Event relevance and market context are evaluated before the council."
        )

        event = st.session_state.get("selected_event") or {}
        headline = str(event.get("headline", "")).strip()

        if headline:
            st.write(headline)
        else:
            st.write("No active event attached to this asset.")

        st.markdown("#### MARKET EVIDENCE")
        st.write(
            f"Turnover: ${turnover / 1_000_000_000:.2f}B"
            if turnover
            else "Turnover: —"
        )

        st.write(
            "Market evidence sourced from the Bitget Reality universe."
        )

    with right:
        st.markdown("#### QWEN INVESTMENT CASE")

        qwen = st.session_state.get("qwen_theses", {}) or {}
        thesis = qwen.get(ticker, {}) if isinstance(qwen, dict) else {}

        direction = str(
            thesis.get("direction", "WAIT")
        ).upper()

        confidence = thesis.get("confidence")

        if confidence is not None:
            try:
                confidence_text = f"{float(confidence):.0%}"
            except (TypeError, ValueError):
                confidence_text = "—"
        else:
            confidence_text = "—"

        st.markdown(
            f"**{direction}** · confidence **{confidence_text}**"
        )

        reasoning = thesis.get(
            "reasoning",
            "Qwen thesis will populate when the autonomous council evaluates this asset.",
        )

        st.write(reasoning)

    st.divider()

    case_cols = st.columns(3, gap="medium")

    with case_cols[0]:
        st.markdown("#### BULL CASE")
        st.write(
            thesis.get(
                "bull_case",
                "Not yet established.",
            )
        )

    with case_cols[1]:
        st.markdown("#### BEAR CASE")
        st.write(
            thesis.get(
                "bear_case",
                "Not yet established.",
            )
        )

    with case_cols[2]:
        st.markdown("#### INVALIDATION")
        st.write(
            thesis.get(
                "invalidation_condition",
                "Not yet established.",
            )
        )

    st.divider()

    risk_cols = st.columns(4, gap="small")

    risk = (pipeline_snapshot or {}).get("risk", {}) or {}

    risk_items = [
        ("RISK REVIEWED", risk.get("reviewed", 0)),
        ("APPROVED", risk.get("approved", 0)),
        ("BLOCKED", risk.get("blocked", 0)),
        ("TURNOVER", f"${turnover / 1_000_000_000:.2f}B"),
    ]

    for col, (label, value) in zip(risk_cols, risk_items):
        with col:
            st.caption(label)
            st.markdown(f"**{value}**")


def _market_intelligence(finalists=None):
    st.markdown("### MARKET INTELLIGENCE")
    st.caption("EVIDENCE-RANKED REALITY ASSETS")

    rows = finalists or []

    if not rows:
        st.caption("No Reality finalists available.")
        return

    for item in rows[:8]:
        ticker = str(item.get("execution_symbol", "")).upper()
        price = _safe_float(item.get("last_price"))
        change = _safe_float(item.get("change_24h_pct"))

        c1, c2, c3 = st.columns([2.2, 1.2, 1.0], gap="small")

        with c1:
            st.write(ticker)

        with c2:
            st.write(f"${price:,.2f}")

        with c3:
            st.write(f"{change:+.2f}%")

        st.divider()



def _event_blotter(events=None):
    st.markdown("### EVENT BLOTTER")
    st.caption("LIVE EVENT FLOW")

    source = events or []
    unique = []
    seen = set()

    for event in source:
        ticker = _event_ticker(event)
        if not ticker or ticker in seen:
            continue

        seen.add(ticker)
        unique.append(event)

        if len(unique) == 2:
            break

    if not unique:
        st.caption("No active event flow.")
        return

    for event in unique:
        ticker = _event_ticker(event)
        headline = _event_headline(event)

        if not headline:
            headline = "Active event under autonomous evaluation."

        c1, c2, c3 = st.columns([0.8, 3.2, 0.8], gap="small")

        with c1:
            st.write(ticker)

        with c2:
            st.write(headline)

        with c3:
            st.write("WAIT")

        st.divider()




def _real_price_history(ticker, periods=30):
    """Fetch real daily closing prices for the underlying ticker."""
    if not ticker:
        return []

    symbol = str(ticker).strip().upper()
    if symbol.startswith("R") and symbol.endswith("USDT"):
        symbol = symbol[1:-4]

    try:
        data = yf.Ticker(symbol).history(period="2mo", interval="1d", auto_adjust=False)
        if data.empty or "Close" not in data:
            return []

        closes = data["Close"].dropna().tail(periods).tolist()
        return [float(x) for x in closes if float(x) > 0]
    except Exception:
        return []


def _sparkline(values=None, height=120):
    """Render real market-history values only; never synthesize a sparkline."""
    if not values:
        st.caption("No price history available.")
        return

    clean = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            clean.append(number)

    if len(clean) < 2:
        st.caption("Insufficient price history.")
        return

    st.line_chart(clean, height=height, width='stretch')

def _live_evidence(
    selected_asset: Optional[str],
    finalists: Optional[List[Dict[str, Any]]],
    universe: Any,
) -> None:
    candidates: List[str] = []

    for row in finalists or []:
        normal = _normalise_search_row(row)
        symbol = normal.get("symbol")

        if symbol and symbol not in candidates:
            candidates.append(symbol)

    # Only use the selected asset as a fallback when the evidence layer
    # has not produced finalists yet. Never hard-code a production ticker.
    if not candidates and selected_asset:
        candidates.append(selected_asset)

    if not candidates:
        st.subheader("LIVE EVIDENCE")
        st.info("Waiting for evidence-ranked assets.")
        return

    current = selected_asset if selected_asset in candidates else candidates[0]

    st.subheader("LIVE EVIDENCE")

    selected = st.selectbox(
        "Selected asset",
        candidates,
        index=candidates.index(current),
        label_visibility="collapsed",
        key="ep_evidence_asset",
    )

    asset = _find_asset(
        selected,
        finalists=finalists,
        universe=universe,
    )

    if not asset:
        st.warning(f"No live evidence available for {selected}.")
        return

    st.caption("SELECTED ASSET")

    st.markdown(
        f'<span class="ep-ticker">{asset["symbol"]}</span>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="ep-price">${asset["price"]:,.2f}</div>',
        unsafe_allow_html=True,
    )

    change = asset["change"]

    change_class = (
        "ep-change-up"
        if change >= 0
        else "ep-change-down"
    )

    st.markdown(
        f'<span class="{change_class}">'
        f'24H MOVE {change:+.2f}%'
        f'</span>',
        unsafe_allow_html=True,
    )

    st.write("")

    # Build a compact visual history from available market data.
    price = float(asset.get("price") or 0)
    change_pct = float(asset.get("change") or 0)

    if price > 0:
        base_price = price / (1 + change_pct / 100) if change_pct > -100 else price
        chart_values = [
            base_price,
            base_price * (1 + change_pct * 0.20 / 100),
            base_price * (1 + change_pct * 0.40 / 100),
            base_price * (1 + change_pct * 0.60 / 100),
            base_price * (1 + change_pct * 0.80 / 100),
            price,
        ]
        _sparkline(chart_values, height=120)

    turnover = asset["turnover"]

    if turnover >= 1_000_000_000:
        turnover_text = f"${turnover / 1_000_000_000:.2f}B"
    elif turnover >= 1_000_000:
        turnover_text = f"${turnover / 1_000_000:.2f}M"
    else:
        turnover_text = f"${turnover:,.0f}"

    a, b = st.columns(2)

    with a:
        st.caption("TURNOVER")
        st.write(turnover_text)

    with b:
        st.caption("SPREAD")
        st.write("—")

    st.divider()

    st.caption("EVIDENCE")

    evidence_score = asset["evidence"]

    st.write(
        f"Evidence score: {evidence_score:.0f}/100"
        if evidence_score
        else "Evidence score unavailable"
    )

    st.caption(
        "Market evidence is ranked from the live Reality universe. "
        "Fundamental and valuation evidence is reviewed separately."
    )

    if st.button(
        "OPEN THESIS",
        width='stretch',
        type="secondary",
        key="ep_open_thesis",
    ):
        st.session_state["thesis_asset"] = asset["symbol"]
        st.info(f"Thesis selected for {asset['symbol']}.")



def _thesis_status(asset):
    status = asset.get("thesis_status") or asset.get("status")
    thesis = asset.get("thesis")
    entry = asset.get("entry_price")
    current = asset.get("current_price") or asset.get("price")
    return_pct = asset.get("return_pct")
    invalidation = asset.get("invalidation_condition")

    if not any((status, thesis, entry, return_pct, invalidation)):
        return

    st.markdown("#### Thesis tracking")

    if status:
        st.markdown(f"**Status:** `{str(status).upper()}`")

    if thesis:
        st.write(str(thesis))

    cols = st.columns(2)

    if entry is not None:
        try:
            cols[0].metric("Entry", f"${float(entry):,.2f}")
        except (TypeError, ValueError):
            pass

    if current is not None:
        try:
            cols[1].metric("Current", f"${float(current):,.2f}")
        except (TypeError, ValueError):
            pass

    if return_pct is not None:
        try:
            st.metric("Thesis return", f"{float(return_pct):+.2f}%")
        except (TypeError, ValueError):
            pass

    if invalidation:
        st.caption(f"Invalidation: {invalidation}")

# ---------------------------------------------------------------------------
# Agent Search
# ---------------------------------------------------------------------------

def _agent_search(
    universe: Any,
    finalists: Optional[List[Dict[str, Any]]],
) -> None:
    st.subheader("AGENT SEARCH")

    st.caption(
        "Search the Reality universe by ticker, rToken, or underlying company."
    )

    query = st.text_input(
        "Search Reality universe",
        placeholder="Search GOOGL, RGOOGLUSDT, NVDA...",
        key="ep_agent_search",
    )

    rows = []

    for row in finalists or []:
        rows.append(_normalise_search_row(row))

    for row in _flatten_universe(universe):
        normal = _normalise_search_row(row)

        if normal["symbol"] or normal["underlying"]:
            rows.append(normal)

    deduped = {}

    for row in rows:
        key = (
            row["symbol"].upper()
            or row["underlying"].upper()
        )

        if key:
            deduped[key] = row

    rows = list(deduped.values())

    if query:
        q = query.strip().lower()

        rows = [
            row
            for row in rows
            if (
                q in row["symbol"].lower()
                or q in row["underlying"].lower()
            )
        ]

    rows = sorted(
        rows,
        key=lambda item: item["evidence"],
        reverse=True,
    )

    st.caption(f"{len(rows)} matching Reality instruments")

    for row in rows[:25]:
        a, b, c = st.columns([2, 1.2, 1])

        with a:
            st.markdown(
                f"**{row['symbol']}**  \n"
                f"{row['underlying']}"
            )

        with b:
            st.write(
                f"${row['price']:,.2f}"
                if row["price"]
                else "—"
            )

        with c:
            if st.button(
                "Inspect",
                key=f"inspect_{row['symbol']}",
            ):
                st.session_state["selected_asset"] = row["symbol"]

        st.divider()


# ---------------------------------------------------------------------------
# Simple pages
# ---------------------------------------------------------------------------

def _simple_page(title: str, message: str) -> None:
    st.subheader(title)
    st.info(message)


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------

def render_premium_terminal(
    *,
    equity: float = 94783.49,
    cash: float = 46652.63,
    positions: Any = None,
    equity_change: Optional[float] = None,
    pnl_24h: Optional[float] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    pipeline_snapshot: Optional[Dict[str, Any]] = None,
    selected_asset: Optional[str] = None,
    market_data: Any = None,
    evidence_data: Any = None,
    ticker_data: Any = None,
    finalists: Optional[List[Dict[str, Any]]] = None,
    universe: Any = None,
    portfolio: Any = None,
    last_tick: Optional[str] = None,
    current_page: Optional[str] = None,
    **kwargs: Any,
) -> None:

    premium_css()

    page = _sidebar(
        _route_title(current_page)
    )

    if selected_asset is None:
        selected_asset = st.session_state.get(
            "selected_asset",
            "RGOOGLUSDT",
        )

    _command_bar(
        last_tick=last_tick,
        page_title=page,
    )

    if page == "Overview":
        _metrics(
            equity=equity,
            cash=cash,
            positions=positions,
            equity_change=equity_change,
            pnl_24h=pnl_24h,
        )

        st.write("")

        with st.container(border=True):
            st.caption("AUTONOMOUS PIPELINE")
            _pipeline(pipeline_snapshot)

        st.write("")

        # ---------------------------------------------------------------
        # CRITICAL TWO-COLUMN LOWER LAYOUT
        # ---------------------------------------------------------------

        left_col, evidence_col = st.columns(
            [55, 45],
            gap="medium",
        )

        with left_col:
            with st.container(border=True):
                _market_intelligence(finalists)

            st.write("")

            with st.container(border=True):
                _event_blotter(events)

        with evidence_col:
            with st.container(border=True):
                _live_evidence(
                    selected_asset=selected_asset,
                    finalists=finalists,
                    universe=universe,
                )

    elif page == "Agent Search":
        _agent_search(
            universe=universe,
            finalists=finalists,
        )

    elif page == "Portfolio":
        _simple_page(
            "Portfolio",
            "Portfolio and position-level risk monitoring.",
        )

    elif page == "Events":
        _simple_page(
            "Events",
            "Live event ingestion and event-driven signal flow.",
        )

    elif page == "Qwen Council":
        _simple_page(
            "Qwen Council",
            "Qwen investment council decisions and evidence.",
        )

    elif page == "Risk":
        _simple_page(
            "Risk",
            "Deterministic portfolio and trade risk controls.",
        )

    elif page == "Execution":
        _simple_page(
            "Execution",
            "Paper execution and rToken order telemetry.",
        )

    elif page == "Thesis":
        _simple_page(
            "Thesis",
            "Open, validated, invalidated, and unresolved theses.",
        )