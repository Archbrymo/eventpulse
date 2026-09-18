from .assets import get_execution_symbol, get_underlying


def get_position(portfolio, ticker):
    execution_symbol = get_execution_symbol(ticker)

    positions = portfolio.get("positions", {})
    position = positions.get(execution_symbol)

    if position is None:
        return {
            "ticker": ticker,
            "execution_symbol": execution_symbol,
            "quantity": 0.0,
            "average_price": 0.0,
            "market_value": 0.0,
        }

    quantity = float(position.get("quantity", 0.0))
    average_price = float(position.get("average_price", 0.0))

    return {
        "ticker": ticker,
        "execution_symbol": execution_symbol,
        "quantity": quantity,
        "average_price": average_price,
        "market_value": quantity * average_price,
    }


def get_portfolio_evidence(
    portfolio,
    ticker,
    current_price,
):
    cash = float(portfolio.get("cash", 0.0))

    position = get_position(
        portfolio,
        ticker,
    )

    quantity = position["quantity"]

    market_value = (
        quantity * float(current_price)
    )

    total_position_value = 0.0

    for symbol, data in portfolio.get(
        "positions",
        {},
    ).items():

        position_quantity = float(
            data.get("quantity", 0.0)
        )

        current_or_entry_price = float(
            data.get("average_price", 0.0)
        )

        total_position_value += (
            position_quantity
            * current_or_entry_price
        )

    estimated_equity = (
        cash + total_position_value
    )

    position_weight = (
        market_value / estimated_equity
        if estimated_equity > 0
        else 0.0
    )

    return {
        "ticker": ticker,
        "execution_symbol": position[
            "execution_symbol"
        ],
        "cash": cash,
        "quantity": quantity,
        "average_price": position[
            "average_price"
        ],
        "current_price": float(current_price),
        "market_value": market_value,
        "estimated_equity": estimated_equity,
        "position_weight": position_weight,
        "has_position": quantity > 0,
    }


def get_portfolio_summary(
    portfolio,
    prices,
):
    cash = float(
        portfolio.get("cash", 0.0)
    )

    positions = portfolio.get(
        "positions",
        {},
    )

    position_values = {}
    total_positions = 0.0

    for execution_symbol, data in positions.items():

        quantity = float(
            data.get("quantity", 0.0)
        )

        average_price = float(
            data.get("average_price", 0.0)
        )

        research_ticker = get_underlying(
            execution_symbol
        )

        price = prices.get(
            research_ticker,
            average_price,
        )

        value = quantity * float(price)

        position_values[
            research_ticker
        ] = value

        total_positions += value

    estimated_equity = (
        cash + total_positions
    )

    weights = {}

    if estimated_equity > 0:

        for ticker, value in (
            position_values.items()
        ):
            weights[ticker] = (
                value / estimated_equity
            )

    return {
        "cash": cash,
        "position_values": position_values,
        "position_weights": weights,
        "total_positions": total_positions,
        "estimated_equity": estimated_equity,
    }


def format_portfolio_for_ai(evidence):
    lines = [
        f"Ticker: {evidence['ticker']}",
        f"Execution asset: {evidence['execution_symbol']}",
        f"Cash available: {evidence['cash']:.2f} USDT",
        f"Current quantity: {evidence['quantity']:.6f}",
        f"Average entry price: {evidence['average_price']:.2f}",
        f"Current price: {evidence['current_price']:.2f}",
        f"Position value: {evidence['market_value']:.2f} USDT",
        f"Estimated portfolio equity: {evidence['estimated_equity']:.2f} USDT",
        f"Position weight: {evidence['position_weight']:.2%}",
        f"Existing position: {'YES' if evidence['has_position'] else 'NO'}",
    ]

    return "\n".join(lines)
