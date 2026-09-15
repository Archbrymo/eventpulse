from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.bitget_universe import (
    discover_rtokens,
    rank_candidates,
    get_bitget_tickers,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def evidence_score(
    candidate: Dict[str, Any],
    event: Optional[Dict[str, Any]] = None,
    portfolio: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Second-stage deterministic research score.

    Input:
        Top ~50 from the cheap market screen.

    Output:
        0-100 research priority score.

    This does NOT make a BUY/SELL decision.
    It only determines which assets deserve expensive
    evidence gathering and Qwen attention.
    """

    ticker = candidate.get("ticker_data") or {}

    turnover = float(
        ticker.get("quote_volume", 0) or 0
    )

    change = float(
        ticker.get("change_pct", 0) or 0
    )

    last = float(
        ticker.get("last", 0) or 0
    )

    bid = float(
        ticker.get("bid", 0) or 0
    )

    ask = float(
        ticker.get("ask", 0) or 0
    )

    score = 0.0

    # -------------------------------------------------
    # Liquidity: 0-25
    # -------------------------------------------------

    if turnover >= 500_000_000:
        score += 25
    elif turnover >= 250_000_000:
        score += 22
    elif turnover >= 100_000_000:
        score += 19
    elif turnover >= 50_000_000:
        score += 16
    elif turnover >= 25_000_000:
        score += 12
    elif turnover >= 10_000_000:
        score += 8
    else:
        score += 4

    # -------------------------------------------------
    # Momentum / catalyst opportunity: 0-20
    # -------------------------------------------------

    abs_change = abs(change)

    if 2 <= abs_change <= 6:
        score += 20
    elif 1 <= abs_change < 2:
        score += 14
    elif 6 < abs_change <= 10:
        score += 15
    elif abs_change > 10:
        score += 8
    else:
        score += 5

    # -------------------------------------------------
    # Directional signal: 0-15
    #
    # Strong positive and negative moves both deserve
    # research because the council can decide BUY,
    # SELL, HOLD, or WAIT.
    # -------------------------------------------------

    if 2 <= abs_change <= 8:
        score += 15
    elif abs_change > 8:
        score += 10
    else:
        score += 5

    # -------------------------------------------------
    # Market quality / spread: 0-15
    # -------------------------------------------------

    if last > 0 and bid > 0 and ask > 0:
        spread_pct = ((ask - bid) / last) * 100

        if spread_pct <= 0.10:
            score += 15
        elif spread_pct <= 0.25:
            score += 12
        elif spread_pct <= 0.50:
            score += 8
        elif spread_pct <= 1.00:
            score += 4

    # -------------------------------------------------
    # Event relevance: 0-15
    # -------------------------------------------------

    if event:
        event_ticker = str(
            event.get("ticker", "")
        ).upper()

        candidate_ticker = str(
            candidate.get("underlying", "")
        ).upper()

        if (
            event_ticker
            and event_ticker == candidate_ticker
        ):
            score += 15
        elif event.get("relevance", 0) >= 0.75:
            score += 5

    # -------------------------------------------------
    # Portfolio diversification: 0-10
    #
    # Prefer candidates that are not already heavily
    # represented in the paper portfolio.
    # -------------------------------------------------

    if portfolio:
        positions = portfolio.get(
            "positions",
            {},
        )

        symbol = candidate.get("symbol", "")

        position = positions.get(symbol)

        if position:
            quantity = float(
                position.get("quantity", 0) or 0
            )

            value = quantity * last

            # Existing exposure gets a modest penalty.
            if value > 10_000:
                score -= 5
            elif value > 5_000:
                score -= 2

        else:
            score += 10

    return round(
        _clamp(score, 0, 100),
        2,
    )


def research_candidates(
    fast_limit: int = 50,
    research_limit: int = 10,
    event: Optional[Dict[str, Any]] = None,
    portfolio: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Convert the fast-screen universe into the finalists
    that should receive deeper evidence and Qwen analysis.
    """

    candidates = rank_candidates(
        limit=fast_limit
    )

    researched = []

    for candidate in candidates:
        row = dict(candidate)

        row["evidence_score"] = evidence_score(
            candidate,
            event=event,
            portfolio=portfolio,
        )

        researched.append(row)

    researched.sort(
        key=lambda x: (
            x["evidence_score"],
            x.get("score", 0),
        ),
        reverse=True,
    )

    return researched[:research_limit]


def print_research_shortlist(
    candidates: List[Dict[str, Any]],
) -> None:

    print()
    print("==============================================")
    print("EVENTPULSE EVIDENCE SHORTLIST")
    print("==============================================")

    for i, candidate in enumerate(
        candidates,
        1,
    ):
        ticker = (
            candidate.get("ticker_data")
            or {}
        )

        print(
            f"{i:2}. "
            f"{candidate['underlying']:8} "
            f"{candidate['symbol']:15} "
            f"evidence={candidate['evidence_score']:5.1f} "
            f"screen={candidate['score']:4.1f} "
            f"24h={ticker.get('change_pct', 0):+7.2f}% "
            f"turnover=${ticker.get('quote_volume', 0):,.0f}"
        )
