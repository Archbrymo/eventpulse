import yfinance as yf


def get_valuation(ticker):
    """
    Collect valuation evidence for the Investment Council.

    This is evidence, not a hard-coded BUY/SELL model.
    Qwen interprets the valuation alongside growth,
    fundamentals, market conditions, and portfolio exposure.
    """

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        forward_pe = info.get("forwardPE")
        earnings_growth = info.get("earningsGrowth")

        peg_approx = None

        if forward_pe is not None and earnings_growth:
            growth_pct = earnings_growth * 100

            if growth_pct > 0:
                peg_approx = forward_pe / growth_pct

        return {
            "ticker": ticker,
            "current_price": info.get("currentPrice"),
            "market_cap": info.get("marketCap"),

            "trailing_pe": info.get("trailingPE"),
            "forward_pe": forward_pe,

            "price_to_sales": info.get(
                "priceToSalesTrailing12Months"
            ),
            "price_to_book": info.get("priceToBook"),

            "enterprise_value": info.get("enterpriseValue"),
            "enterprise_value_to_revenue": info.get(
                "enterpriseToRevenue"
            ),
            "enterprise_value_to_ebitda": info.get(
                "enterpriseToEbitda"
            ),

            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": earnings_growth,

            "peg_approx": peg_approx,

            "target_mean_price": info.get(
                "targetMeanPrice"
            ),
            "target_high_price": info.get(
                "targetHighPrice"
            ),
            "target_low_price": info.get(
                "targetLowPrice"
            ),

            "recommendation": info.get(
                "recommendationKey"
            ),
            "analyst_count": info.get(
                "numberOfAnalystOpinions"
            ),
        }

    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
        }


def get_valuation_signals(data):
    """
    Produce descriptive valuation observations.

    These are NOT trading decisions.
    """

    if "error" in data:
        return {
            "status": "unavailable",
            "observations": [data["error"]],
        }

    observations = []

    forward_pe = data.get("forward_pe")
    trailing_pe = data.get("trailing_pe")
    growth = data.get("earnings_growth")
    peg = data.get("peg_approx")

    if forward_pe is not None:

        if forward_pe > 50:
            observations.append(
                "Forward P/E is very elevated; substantial "
                "future growth may already be reflected in the price."
            )

        elif forward_pe > 30:
            observations.append(
                "Forward P/E is elevated and requires strong "
                "future growth to justify the valuation."
            )

        elif forward_pe < 15:
            observations.append(
                "Forward P/E is relatively low."
            )

    if (
        trailing_pe is not None
        and forward_pe is not None
        and trailing_pe > forward_pe
    ):
        observations.append(
            "Forward P/E is below trailing P/E, suggesting "
            "expected earnings growth may improve the valuation."
        )

    if growth is not None:
        observations.append(
            f"Earnings growth is approximately {growth:.1%}."
        )

    if peg is not None:

        if peg < 1:
            observations.append(
                "Approximate PEG is below 1, indicating "
                "growth may be strong relative to the earnings multiple."
            )

        elif peg > 2:
            observations.append(
                "Approximate PEG is above 2, indicating "
                "a demanding valuation relative to expected growth."
            )

    target = data.get("target_mean_price")
    current = data.get("current_price")

    if target is not None and current is not None and current > 0:

        upside = (target / current) - 1

        observations.append(
            f"Analyst consensus target implies approximately "
            f"{upside:.1%} potential upside/downside."
        )

    if not observations:
        observations.append(
            "Insufficient valuation evidence for a strong conclusion."
        )

    return {
        "status": "available",
        "observations": observations,
    }


def format_valuation_for_ai(data):
    """
    Convert valuation evidence into compact text for Qwen.
    """

    if "error" in data:
        return f"Valuation data unavailable: {data['error']}"

    signals = get_valuation_signals(data)

    lines = [
        f"Ticker: {data.get('ticker')}",
    ]

    fields = [
        ("Current price", "current_price"),
        ("Market cap", "market_cap"),
        ("Trailing P/E", "trailing_pe"),
        ("Forward P/E", "forward_pe"),
        ("Price / sales", "price_to_sales"),
        ("Price / book", "price_to_book"),
        ("EV / revenue", "enterprise_value_to_revenue"),
        ("EV / EBITDA", "enterprise_value_to_ebitda"),
        ("Revenue growth", "revenue_growth"),
        ("Earnings growth", "earnings_growth"),
        ("Approximate PEG", "peg_approx"),
        ("Analyst target", "target_mean_price"),
        ("Analyst count", "analyst_count"),
        ("Analyst recommendation", "recommendation"),
    ]

    for label, key in fields:

        value = data.get(key)

        if value is not None:
            lines.append(f"{label}: {value}")

    lines.append("")
    lines.append("Valuation observations:")

    for observation in signals["observations"]:
        lines.append(f"- {observation}")

    return "\n".join(lines)
