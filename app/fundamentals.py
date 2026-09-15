import yfinance as yf


def get_fundamentals(ticker):
    """
    Collect fundamental company data for the AI Investment Council.
    """

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "ticker": ticker,

            "company": info.get("longName") or info.get("shortName"),

            "sector": info.get("sector"),
            "industry": info.get("industry"),

            "market_cap": info.get("marketCap"),

            "revenue": info.get("totalRevenue"),
            "revenue_growth": info.get("revenueGrowth"),

            "gross_margin": info.get("grossMargins"),
            "operating_margin": info.get("operatingMargins"),
            "profit_margin": info.get("profitMargins"),

            "earnings_growth": info.get("earningsGrowth"),
            "earnings_quarterly_growth": info.get(
                "earningsQuarterlyGrowth"
            ),

            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),

            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),

            "free_cash_flow": info.get("freeCashflow"),

            "trailing_eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),

            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),

            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "price_to_book": info.get("priceToBook"),

            "dividend_yield": info.get("dividendYield"),
        }

    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
        }


def format_fundamentals_for_ai(data):
    """
    Convert raw fundamental data into a compact format
    suitable for the Qwen Investment Council.
    """

    if "error" in data:
        return f"Fundamental data unavailable: {data['error']}"

    lines = []

    fields = [
        ("Company", "company"),
        ("Sector", "sector"),
        ("Industry", "industry"),
        ("Market cap", "market_cap"),
        ("Revenue", "revenue"),
        ("Revenue growth", "revenue_growth"),
        ("Gross margin", "gross_margin"),
        ("Operating margin", "operating_margin"),
        ("Profit margin", "profit_margin"),
        ("Earnings growth", "earnings_growth"),
        ("ROE", "return_on_equity"),
        ("ROA", "return_on_assets"),
        ("Debt / equity", "debt_to_equity"),
        ("Current ratio", "current_ratio"),
        ("Free cash flow", "free_cash_flow"),
        ("Trailing EPS", "trailing_eps"),
        ("Forward EPS", "forward_eps"),
        ("Trailing P/E", "trailing_pe"),
        ("Forward P/E", "forward_pe"),
        ("Price / sales", "price_to_sales"),
        ("Price / book", "price_to_book"),
        ("Dividend yield", "dividend_yield"),
    ]

    for label, key in fields:
        value = data.get(key)

        if value is not None:
            lines.append(f"{label}: {value}")

    return "\n".join(lines)
