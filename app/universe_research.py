from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.bitget_universe import (
    discover_rtokens,
    rank_candidates,
    get_bitget_tickers,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def evidence_breakdown(
    candidate: Dict[str, Any],
    event: Optional[Dict[str, Any]] = None,
    portfolio: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """
    Return the individual evidence components used by the
    deterministic evidence ranking layer.

    Components intentionally preserve the existing scoring model:
    liquidity 0-25, momentum 0-20, directional signal 0-15,
    market quality 0-15, event relevance 0-15,
    diversification 0-10.
    """

    ticker = candidate.get("ticker_data") or {}
    turnover = float(ticker.get("turnover", 0) or 0)
    change = float(ticker.get("change24h", 0) or 0)
    last = float(ticker.get("last", 0) or 0)
    bid = float(ticker.get("bid", 0) or 0)
    ask = float(ticker.get("ask", 0) or 0)

    liquidity = 4.0
    if turnover >= 500_000_000:
        liquidity = 25.0
    elif turnover >= 250_000_000:
        liquidity = 22.0
    elif turnover >= 100_000_000:
        liquidity = 19.0
    elif turnover >= 50_000_000:
        liquidity = 16.0
    elif turnover >= 25_000_000:
        liquidity = 12.0
    elif turnover >= 10_000_000:
        liquidity = 8.0

    abs_change = abs(change)

    if 2 <= abs_change <= 6:
        momentum = 20.0
    elif 1 <= abs_change < 2:
        momentum = 14.0
    elif 6 < abs_change <= 10:
        momentum = 15.0
    elif abs_change > 10:
        momentum = 8.0
    else:
        momentum = 5.0

    if 2 <= abs_change <= 8:
        directional = 15.0
    elif abs_change > 8:
        directional = 10.0
    else:
        directional = 5.0

    market_quality = 0.0
    if last > 0 and bid > 0 and ask > 0:
        spread_pct = ((ask - bid) / last) * 100

        if spread_pct <= 0.10:
            market_quality = 15.0
        elif spread_pct <= 0.25:
            market_quality = 12.0
        elif spread_pct <= 0.50:
            market_quality = 8.0
        elif spread_pct <= 1.00:
            market_quality = 4.0

    event_relevance = 0.0
    if event:
        event_ticker = str(event.get("ticker", "")).upper()
        candidate_ticker = str(
            candidate.get("underlying", "")
        ).upper()

        if event_ticker and event_ticker == candidate_ticker:
            event_relevance = 15.0
        elif event.get("relevance", 0) >= 0.75:
            event_relevance = 5.0

    diversification = 0.0
    if portfolio:
        positions = portfolio.get("positions", {})
        symbol = candidate.get("symbol", "")
        position = positions.get(symbol)

        if position:
            quantity = float(
                position.get("quantity", 0) or 0
            )
            value = quantity * last

            if value > 10_000:
                diversification = -5.0
            elif value > 5_000:
                diversification = -2.0
            else:
                diversification = 0.0
        else:
            diversification = 10.0

    return {
        "liquidity": liquidity,
        "momentum": momentum,
        "directional": directional,
        "market_quality": market_quality,
        "event_relevance": event_relevance,
        "diversification": diversification,
    }


def evidence_score(
    candidate: Dict[str, Any],
    event: Optional[Dict[str, Any]] = None,
    portfolio: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Preserve the existing deterministic evidence score while
    deriving it from the auditable component breakdown.
    """

    components = evidence_breakdown(
        candidate,
        event=event,
        portfolio=portfolio,
    )

    return round(
        _clamp(sum(components.values()), 0, 100),
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

        row["evidence_breakdown"] = evidence_breakdown(
            candidate,
            event=event,
            portfolio=portfolio,
        )

        row["evidence_score"] = round(
            _clamp(
                sum(row["evidence_breakdown"].values()),
                0,
                100,
            ),
            2,
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
