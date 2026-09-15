from app.fundamentals import (
    get_fundamentals,
    format_fundamentals_for_ai,
)
from app.valuation import (
    get_valuation,
    format_valuation_for_ai,
)


def build_research_pack(
    finalists,
    event=None,
    include_fundamentals=True,
):
    """
    Build the compact evidence package sent to Qwen.

    Only finalists are enriched with fundamentals/valuation
    so we do not make expensive external requests across
    the entire Reality universe.
    """

    event = event or {}
    event_ticker = str(
        event.get("ticker", "")
    ).upper()

    pack = []

    for candidate in finalists:
        ticker_data = candidate.get(
            "ticker_data",
            {},
        )

        price = float(
            ticker_data.get("last", 0.0)
        )

        bid = float(
            ticker_data.get("bid", 0.0)
        )

        ask = float(
            ticker_data.get("ask", 0.0)
        )

        spread_pct = (
            ((ask - bid) / price) * 100.0
            if price > 0
            else 0.0
        )

        underlying = candidate.get(
            "underlying",
            "",
        )

        item = {
            "ticker": underlying,
            "execution_symbol": candidate.get(
                "symbol"
            ),
            "last_price": price,
            "change_24h_pct": float(
                ticker_data.get(
                    "change_pct",
                    0.0,
                )
            ),
            "turnover_24h": float(
                ticker_data.get(
                    "quote_volume",
                    0.0,
                )
            ),
            "bid": bid,
            "ask": ask,
            "spread_pct": spread_pct,
            "fast_score": float(
                candidate.get(
                    "score",
                    0.0,
                )
            ),
            "evidence_score": float(
                candidate.get(
                    "evidence_score",
                    0.0,
                )
            ),
            "event_relevant": (
                underlying.upper()
                == event_ticker
            ),
        }

        if include_fundamentals:
            print(
                f"  Enriching {underlying} "
                f"with fundamentals/valuation..."
            )

            fundamentals = get_fundamentals(
                underlying
            )

            valuation = get_valuation(
                underlying
            )

            item["fundamentals"] = fundamentals
            item["valuation"] = valuation

            item["fundamentals_text"] = (
                format_fundamentals_for_ai(
                    fundamentals
                )
            )

            item["valuation_text"] = (
                format_valuation_for_ai(
                    valuation
                )
            )

        pack.append(item)

    return pack


def format_for_qwen(research_pack):
    """
    Convert the research pack into compact evidence text.
    """

    sections = []

    for i, item in enumerate(
        research_pack,
        1,
    ):
        sections.append(
            f"""
FINALIST {i}: {item['ticker']}
Execution symbol: {item['execution_symbol']}
Price: {item['last_price']}
24h move: {item['change_24h_pct']:+.2f}%
24h turnover: ${item['turnover_24h']:,.0f}
Bid: {item['bid']}
Ask: {item['ask']}
Spread: {item['spread_pct']:.3f}%
Fast score: {item['fast_score']:.1f}
Evidence score: {item['evidence_score']:.1f}
Event relevant: {item['event_relevant']}

FUNDAMENTALS:
{item.get('fundamentals_text', 'Unavailable')}

VALUATION:
{item.get('valuation_text', 'Unavailable')}
""".strip()
        )

    return "\n\n".join(sections)
