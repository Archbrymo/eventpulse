from html import escape
from datetime import datetime

import pandas as pd
import streamlit as st


CSS = """
<style>
.stApp {
    background:
        linear-gradient(rgba(30,42,58,.11) 1px, transparent 1px),
        linear-gradient(90deg, rgba(30,42,58,.11) 1px, transparent 1px),
        radial-gradient(circle at 75% 0%, rgba(15,48,78,.18), transparent 35%),
        #070B14;
    background-size: 42px 42px, 42px 42px, auto;
}

.block-container {
    max-width: 1500px;
    padding-top: 1rem;
}

section[data-testid="stSidebar"] {
    background: #080D16;
    border-right: 1px solid #1E2A3A;
}

section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
    gap: 2px;
}

section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    border: 1px solid transparent;
    padding: 8px 10px;
    margin: 0;
    color: #91A0B5;
}

section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
    border-color: #24415A;
    background: #0C1826;
    color: #7DD3FC;
}

section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label p {
    font-family: "IBM Plex Mono", monospace;
    font-size: 11px;
}

h1, h2, h3, h4,
[data-testid="stMetricValue"] {
    font-family: "IBM Plex Mono", monospace !important;
}

[data-testid="stMetric"] {
    background: #0E1522;
    border: 1px solid #1E2A3A;
    border-radius: 2px;
    padding: 13px 15px;
}

[data-testid="stMetricLabel"] {
    color: #7F8DA3 !important;
    font-family: "IBM Plex Mono", monospace !important;
    font-size: 9px !important;
    letter-spacing: .12em;
}

[data-testid="stMetricValue"] {
    color: #E8EDF5 !important;
    font-size: 23px !important;
}

.stButton button {
    border: 1px solid #1E2A3A;
    background: #0A111C;
    color: #7DD3FC;
    border-radius: 2px;
    font-family: "IBM Plex Mono", monospace;
}

[data-testid="stExpander"] {
    border: 1px solid #1E2A3A !important;
    border-radius: 2px !important;
    background: #0A111C;
}

.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div {
    background: #0A111C !important;
    border-color: #1E2A3A !important;
    border-radius: 2px !important;
    color: #E8EDF5 !important;
    font-family: "IBM Plex Mono", monospace !important;
}

hr {
    border-color: #1E2A3A !important;
}

.ep-tape {
    overflow: hidden;
    white-space: nowrap;
    border-top: 1px solid #1E2A3A;
    border-bottom: 1px solid #1E2A3A;
    background: #060B13;
    margin-bottom: 14px;
}

.ep-tape-inner {
    display: inline-block;
    min-width: max-content;
    padding: 7px 0;
    animation: ep-scroll 42s linear infinite;
}

.ep-tick {
    display: inline-block;
    margin-right: 28px;
    font-family: "IBM Plex Mono", monospace;
    font-size: 10px;
}

.ep-symbol {
    color: #7DD3FC;
}

.ep-price {
    color: #E8EDF5;
    margin-left: 5px;
}

.ep-up {
    color: #0ECB81;
    margin-left: 5px;
}

.ep-down {
    color: #F6465D;
    margin-left: 5px;
}

@keyframes ep-scroll {
    from { transform: translateX(0); }
    to { transform: translateX(-50%); }
}

.ep-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid #1E2A3A;
    padding: 4px 0 12px;
}

.ep-logo {
    color: #7DD3FC;
    font-family: "IBM Plex Mono", monospace;
    font-size: 24px;
    font-weight: 600;
    letter-spacing: .04em;
}

.ep-subtitle {
    color: #7F8DA3;
    font-family: "IBM Plex Mono", monospace;
    font-size: 10px;
}

.ep-session {
    display: flex;
    gap: 18px;
    border-bottom: 1px solid #1E2A3A;
    padding: 7px 0;
    margin-bottom: 14px;
    color: #7F8DA3;
    font-family: "IBM Plex Mono", monospace;
    font-size: 9px;
    letter-spacing: .08em;
}

.ep-live {
    color: #7DD3FC;
}

.ep-paper {
    color: #F0B90B;
}

.ep-hero {
    background: #0E1522;
    border: 1px solid #1E2A3A;
    padding: 12px 15px;
}

.ep-label {
    color: #7F8DA3;
    font-family: "IBM Plex Mono", monospace;
    font-size: 9px;
    letter-spacing: .12em;
}

.ep-pnl {
    font-family: "IBM Plex Mono", monospace;
    font-size: 27px;
    margin-top: 7px;
}

.ep-book {
    color: #7F8DA3;
    font-family: "IBM Plex Mono", monospace;
    font-size: 10px;
    margin: 7px 0 12px;
}

.ep-section {
    color: #7DD3FC;
    font-family: "IBM Plex Mono", monospace;
    font-size: 10px;
    letter-spacing: .13em;
    margin: 18px 0 8px;
}

.ep-event-head,
.ep-event-row {
    display: grid;
    grid-template-columns:
        80px 105px 75px minmax(260px,1fr)
        70px 90px 100px;
    gap: 8px;
    align-items: center;
}

.ep-event-head {
    padding: 7px 10px;
    border-top: 1px solid #1E2A3A;
    border-bottom: 1px solid #1E2A3A;
    color: #7F8DA3;
    font-family: "IBM Plex Mono", monospace;
    font-size: 8px;
    letter-spacing: .1em;
}

.ep-event-row {
    padding: 9px 10px;
    border-bottom: 1px solid #162233;
    background: rgba(14,21,34,.65);
    font-family: "IBM Plex Mono", monospace;
    font-size: 9px;
}

.ep-time,
.ep-source,
.ep-gate {
    color: #7F8DA3;
}

.ep-ticker {
    color: #7DD3FC;
    font-weight: 600;
}

.ep-title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.ep-chip {
    display: inline-block;
    padding: 3px 6px;
    border: 1px solid #1E2A3A;
    background: #0A111C;
    font-family: "IBM Plex Mono", monospace;
    font-size: 8px;
}

.ep-blue {
    color: #7DD3FC;
    border-color: #24506A;
}

.ep-green {
    color: #0ECB81;
    border-color: #17583F;
}

.ep-red {
    color: #F6465D;
    border-color: #652333;
}

.ep-yellow {
    color: #F0B90B;
    border-color: #5B4815;
}

.ep-receipt {
    border-left: 2px solid #24415A;
    padding-left: 12px;
}

.ep-receipt-row {
    display: grid;
    grid-template-columns: 110px 1fr;
    gap: 10px;
    padding: 5px 0;
    border-bottom: 1px solid #162233;
    font-family: "IBM Plex Mono", monospace;
    font-size: 10px;
}

.ep-key {
    color: #7F8DA3;
    font-size: 8px;
}

.ep-footer {
    border-top: 1px solid #1E2A3A;
    margin-top: 30px;
    padding-top: 8px;
    color: #7F8DA3;
    font-family: "IBM Plex Mono", monospace;
    font-size: 8px;
}
</style>
"""


def css():
    st.markdown(CSS, unsafe_allow_html=True)


def render_ticker(tickers):
    parts = []

    for item in tickers:
        symbol = escape(str(item.get("symbol", "")))
        price = float(item.get("price", 0) or 0)
        change = float(item.get("change_pct", 0) or 0)

        cls = "ep-up" if change >= 0 else "ep-down"
        sign = "+" if change >= 0 else ""

        parts.append(
            f'<span class="ep-tick">'
            f'<span class="ep-symbol">{symbol}</span>'
            f'<span class="ep-price">{price:,.2f}</span>'
            f'<span class="{cls}">{sign}{change:.2f}%</span>'
            f'</span>'
        )

    if not parts:
        parts = [
            '<span class="ep-tick">'
            '<span class="ep-symbol">rTOKEN</span>'
            '<span class="ep-price">MARKET DATA WAITING</span>'
            '</span>'
        ]

    tape = "".join(parts)

    st.markdown(
        f'<div class="ep-tape">'
        f'<div class="ep-tape-inner">'
        f'{tape}{tape}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def render_header(last_tick=None):
    last_tick = last_tick or datetime.now().strftime("%H:%M:%S")

    st.markdown(
        '<div class="ep-header">'
        '<span class="ep-logo">EVENTPULSE</span>'
        '<span class="ep-subtitle">'
        'Event-driven autonomous trading terminal'
        '</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="ep-session">'
        f'<span>US CASH CLOSED</span>'
        f'<span class="ep-live">rTOKEN 24H LIVE</span>'
        f'<span class="ep-paper">PAPER</span>'
        f'<span>LAST TICK {escape(str(last_tick))}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_kpis(
    equity,
    cash,
    positions,
    equity_24h_ago=None,
):
    if equity_24h_ago is None:
        equity_24h_ago = equity

    pnl = equity - equity_24h_ago

    pnl_pct = (
        pnl / equity_24h_ago * 100
        if equity_24h_ago
        else 0
    )

    color = "#0ECB81" if pnl >= 0 else "#F6465D"
    sign = "+" if pnl >= 0 else ""

    st.markdown(
        f'<div class="ep-hero">'
        f'<div class="ep-label">24H PNL</div>'
        f'<div class="ep-pnl" style="color:{color}">'
        f'{sign}${abs(pnl):,.2f} '
        f'<span style="font-size:11px">'
        f'{sign}{pnl_pct:.2f}%'
        f'</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    a, b, c = st.columns(3)

    with a:
        st.metric("EQUITY", f"${equity:,.2f}")

    with b:
        st.metric("CASH", f"${cash:,.2f}")

    with c:
        st.metric("OPEN POSITIONS", len(positions))

    if positions:
        book = " · ".join(
            f"{x['ticker']} {x['quantity']:g}"
            for x in positions[:6]
        )
    else:
        book = "flat"

    st.markdown(
        f'<div class="ep-book">'
        f'BOOK · {escape(book)} · cash {cash:,.2f}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _status(row):
    status = str(
        row.get("status", "NEW")
    ).upper().strip()

    if status in {"FILLED", "EXECUTED", "PAPER FILL"}:
        return "PAPER FILL", "ep-green"

    if status in {"BLOCK", "BLOCKED", "REJECTED"}:
        return "BLOCKED", "ep-red"

    if status in {"SENT", "SUBMITTED", "ORDER SENT"}:
        return "SENT", "ep-yellow"

    if status in {"SCORED", "RESEARCHED"}:
        return "SCORED", "ep-blue"

    return "NEW", "ep-blue"


def _value(row, *keys, default="—"):
    for key in keys:
        value = row.get(key)

        if value is not None:
            value = str(value).strip()

            if value and value.lower() not in {
                "nan",
                "none",
            }:
                return value

    return default


def _time(value):
    try:
        dt = pd.to_datetime(value)

        if pd.isna(dt):
            return "--:--:-- ET"

        return dt.strftime("%H:%M:%S ET")
    except Exception:
        return str(value)[:8]


def render_event_blotter(df, max_rows=12):
    if df is None or df.empty:
        st.info("No event records available.")
        return

    data = df.copy()

    if "timestamp" in data.columns:
        data["_dt"] = pd.to_datetime(
            data["timestamp"],
            errors="coerce",
        )

        data = data.sort_values(
            "_dt",
            ascending=False,
        )

    dedupe = [
        c
        for c in [
            "timestamp",
            "title",
            "ticker",
        ]
        if c in data.columns
    ]

    if dedupe:
        data = data.drop_duplicates(
            subset=dedupe,
            keep="first",
        )

    data = data.head(max_rows)

    st.markdown(
        '<div class="ep-event-head">'
        '<div>TIME</div>'
        '<div>SOURCE</div>'
        '<div>TICKER</div>'
        '<div>EVENT</div>'
        '<div>BIAS</div>'
        '<div>GATE</div>'
        '<div>STATUS</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    for _, row in data.iterrows():
        timestamp = _time(
            row.get("timestamp")
        )

        source = _value(
            row,
            "source",
            "provider",
            default="EVENT ENGINE",
        )

        ticker = _value(
            row,
            "ticker",
            "symbol",
        )

        title = _value(
            row,
            "title",
            default="Untitled event",
        )

        summary = _value(
            row,
            "summary",
            default="No summary available.",
        )

        bias = _value(
            row,
            "bias",
            "direction",
            "signal",
            default="WAIT",
        ).upper()

        gate = _value(
            row,
            "gate",
            "risk_gate",
            "risk_status",
            default="PENDING",
        ).upper()

        status, chip = _status(row)

        st.markdown(
            f'<div class="ep-event-row">'
            f'<div class="ep-time">{escape(timestamp)}</div>'
            f'<div class="ep-source">{escape(source)}</div>'
            f'<div class="ep-ticker">{escape(ticker)}</div>'
            f'<div class="ep-title" title="{escape(title)}">'
            f'{escape(title)}</div>'
            f'<div>{escape(bias)}</div>'
            f'<div class="ep-gate">{escape(gate)}</div>'
            f'<div><span class="ep-chip {chip}">'
            f'{escape(status)}'
            f'</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.expander(
            f"{timestamp} · {ticker} · {title[:80]}"
        ):
            st.markdown(
                "**EVENT → JUDGMENT → GATE → ORDER**"
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.caption("EVENT")
                st.write(title)

            with c2:
                st.caption("JUDGMENT")
                st.write(bias)

            with c3:
                st.caption("GATE")
                st.write(gate)

            with c4:
                st.caption("ORDER")
                st.write(
                    _value(
                        row,
                        "order",
                        "execution_symbol",
                        default="NONE",
                    )
                )

            st.markdown(
                f'<div class="ep-receipt">'
                f'<div class="ep-receipt-row">'
                f'<div class="ep-key">SOURCE</div>'
                f'<div>{escape(source)}</div>'
                f'</div>'
                f'<div class="ep-receipt-row">'
                f'<div class="ep-key">TICKER</div>'
                f'<div>{escape(ticker)}</div>'
                f'</div>'
                f'<div class="ep-receipt-row">'
                f'<div class="ep-key">SUMMARY</div>'
                f'<div>{escape(summary)}</div>'
                f'</div>'
                f'<div class="ep-receipt-row">'
                f'<div class="ep-key">STATUS</div>'
                f'<div>{escape(status)}</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_event_filters(df):
    if df is None or df.empty:
        return df

    tickers = ["ALL"]

    if "ticker" in df.columns:
        tickers += sorted(
            df["ticker"]
            .dropna()
            .astype(str)
            .str.upper()
            .unique()
            .tolist()
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        ticker = st.selectbox(
            "TICKER",
            tickers,
        )

    with c2:
        status = st.selectbox(
            "STATUS",
            [
                "ALL",
                "NEW",
                "SCORED",
                "BLOCKED",
                "SENT",
                "PAPER FILL",
            ],
        )

    with c3:
        window = st.selectbox(
            "WINDOW",
            ["1H", "8H", "24H", "ALL"],
            index=2,
        )

    result = df.copy()

    if ticker != "ALL" and "ticker" in result:
        result = result[
            result["ticker"]
            .astype(str)
            .str.upper()
            .eq(ticker)
        ]

    if status != "ALL":
        result = result[
            result.apply(
                lambda row:
                    _status(row)[0] == status,
                axis=1,
            )
        ]

    if (
        window != "ALL"
        and "timestamp" in result.columns
    ):
        hours = {
            "1H": 1,
            "8H": 8,
            "24H": 24,
        }[window]

        timestamps = pd.to_datetime(
            result["timestamp"],
            errors="coerce",
        )

        result = result[
            timestamps
            >= pd.Timestamp.now()
            - pd.Timedelta(hours=hours)
        ]

    return result


def render_events_page(
    events_df,
    equity,
    cash,
    positions,
    equity_24h_ago,
    ticker_data,
):
    css()

    ticker_tape(ticker_data)

    render_header()

    render_kpis(
        equity=equity,
        cash=cash,
        positions=positions,
        equity_24h_ago=equity_24h_ago,
    )

    st.markdown(
        '<div class="ep-section">EVENT TAPE</div>',
        unsafe_allow_html=True,
    )

    filtered = render_event_filters(
        events_df
    )

    render_event_blotter(
        filtered,
        max_rows=12,
    )

    st.markdown(
        '<div class="ep-footer">'
        'EventPulse | Bitget Reality rToken paper execution'
        '</div>',
        unsafe_allow_html=True,
    )
