import yfinance as yf


def get_market_data(ticker, period="3mo"):
    """
    Collect market-behavior evidence for the Investment Council.
    """

    try:
        stock = yf.Ticker(ticker)

        data = stock.history(
            period=period,
            interval="1d"
        )

        if data.empty:
            return {
                "ticker": ticker,
                "error": "No market data available",
            }

        close = data["Close"].dropna()
        volume = data["Volume"].dropna()

        if len(close) < 20:
            return {
                "ticker": ticker,
                "error": "Insufficient market history",
            }

        current_price = float(close.iloc[-1])

        sma20 = float(
            close.rolling(20).mean().iloc[-1]
        )

        sma50 = None

        if len(close) >= 50:
            sma50 = float(
                close.rolling(50).mean().iloc[-1]
            )

        return_5d = None
        return_20d = None
        return_60d = None

        if len(close) >= 6:
            return_5d = float(
                close.iloc[-1] / close.iloc[-6] - 1
            )

        if len(close) >= 21:
            return_20d = float(
                close.iloc[-1] / close.iloc[-21] - 1
            )

        if len(close) >= 61:
            return_60d = float(
                close.iloc[-1] / close.iloc[-61] - 1
            )

        daily_returns = close.pct_change().dropna()

        volatility = None

        if len(daily_returns) >= 20:
            volatility = float(
                daily_returns.tail(20).std() * (252 ** 0.5)
            )

        average_volume_20 = float(
            volume.tail(20).mean()
        )

        current_volume = float(volume.iloc[-1])

        volume_ratio = None

        if average_volume_20 > 0:
            volume_ratio = (
                current_volume / average_volume_20
            )

        distance_from_20sma = (
            current_price / sma20 - 1
        )

        distance_from_50sma = None

        if sma50:
            distance_from_50sma = (
                current_price / sma50 - 1
            )

        trend_20 = (
            "ABOVE_20DMA"
            if current_price > sma20
            else "BELOW_20DMA"
        )

        if sma50:
            trend_50 = (
                "ABOVE_50DMA"
                if current_price > sma50
                else "BELOW_50DMA"
            )
        else:
            trend_50 = "UNAVAILABLE"

        return {
            "ticker": ticker,
            "current_price": current_price,
            "sma20": sma20,
            "sma50": sma50,
            "distance_from_20sma": distance_from_20sma,
            "distance_from_50sma": distance_from_50sma,
            "return_5d": return_5d,
            "return_20d": return_20d,
            "return_60d": return_60d,
            "annualized_volatility": volatility,
            "current_volume": current_volume,
            "average_volume_20": average_volume_20,
            "volume_ratio": volume_ratio,
            "trend_20": trend_20,
            "trend_50": trend_50,
        }

    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
        }


def get_market_signals(data):

    if "error" in data:
        return {
            "status": "unavailable",
            "observations": [data["error"]],
        }

    observations = []

    price = data.get("current_price")
    sma20 = data.get("sma20")
    sma50 = data.get("sma50")

    if price and sma20:
        if price > sma20:
            observations.append(
                "Price is above the 20-day moving average."
            )
        else:
            observations.append(
                "Price is below the 20-day moving average."
            )

    if price and sma50:
        if price > sma50:
            observations.append(
                "Price is above the 50-day moving average."
            )
        else:
            observations.append(
                "Price is below the 50-day moving average."
            )

    if data.get("return_5d") is not None:
        observations.append(
            f"5-day return is approximately "
            f"{data['return_5d']:.1%}."
        )

    if data.get("return_20d") is not None:
        observations.append(
            f"20-day return is approximately "
            f"{data['return_20d']:.1%}."
        )

    volume_ratio = data.get("volume_ratio")

    if volume_ratio is not None:

        if volume_ratio >= 1.5:
            observations.append(
                "Recent volume is significantly above "
                "its 20-day average."
            )

        elif volume_ratio <= 0.7:
            observations.append(
                "Recent volume is below its 20-day average."
            )

        else:
            observations.append(
                "Recent volume is near its normal 20-day range."
            )

    volatility = data.get("annualized_volatility")

    if volatility is not None:
        observations.append(
            f"Annualized volatility is approximately "
            f"{volatility:.1%}."
        )

    if not observations:
        observations.append(
            "Insufficient market evidence for a strong conclusion."
        )

    return {
        "status": "available",
        "observations": observations,
    }


def format_market_for_ai(data):

    if "error" in data:
        return f"Market data unavailable: {data['error']}"

    signals = get_market_signals(data)

    lines = [
        f"Ticker: {data.get('ticker')}",
    ]

    fields = [
        ("Current price", "current_price"),
        ("20-day moving average", "sma20"),
        ("50-day moving average", "sma50"),
        ("Distance from 20DMA", "distance_from_20sma"),
        ("Distance from 50DMA", "distance_from_50sma"),
        ("5-day return", "return_5d"),
        ("20-day return", "return_20d"),
        ("60-day return", "return_60d"),
        ("Annualized volatility", "annualized_volatility"),
        ("Volume ratio", "volume_ratio"),
        ("20-day trend", "trend_20"),
        ("50-day trend", "trend_50"),
    ]

    for label, key in fields:
        value = data.get(key)

        if value is not None:
            lines.append(f"{label}: {value}")

    lines.append("")
    lines.append("Market observations:")

    for observation in signals["observations"]:
        lines.append(f"- {observation}")

    return "\n".join(lines)


def get_prices(tickers):
    """
    Return prices keyed by the symbols requested by the caller.

    Yahoo Finance uses the underlying U.S. ticker symbols, while
    EventPulse execution uses rToken symbols such as rAAPL.
    """

    from .assets import get_underlying

    prices = {}

    for ticker in tickers:
        requested_symbol = ticker

        # Convert rToken symbols such as rAAPL -> AAPL
        yahoo_symbol = get_underlying(ticker)

        data = get_market_data(yahoo_symbol)

        if "current_price" in data:
            prices[requested_symbol] = data["current_price"]
        else:
            print(
                f"Warning: no price data for {requested_symbol}"
            )

    return prices

