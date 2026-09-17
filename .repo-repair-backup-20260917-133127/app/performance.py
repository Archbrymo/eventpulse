from .database import (
    get_trades,
    get_equity_history,
    load_initial_portfolio,
    load_portfolio,
)
from .market import get_prices


def build_fifo_lots(trades, initial_positions):
    lots = {}

    for ticker, position in initial_positions.items():
        quantity = float(position["quantity"])
        price = float(position["average_price"])

        if quantity > 0:
            lots[ticker] = [{"quantity": quantity, "price": price}]

    for trade in trades:
        ticker = trade[2]
        direction = trade[3]
        quantity = float(trade[4])
        price = float(trade[5])

        if ticker not in lots:
            lots[ticker] = []

        if direction == "BUY":
            lots[ticker].append({
                "quantity": quantity,
                "price": price,
            })

        elif direction == "SELL":
            remaining = quantity

            while remaining > 0 and lots[ticker]:
                lot = lots[ticker][0]

                matched = min(
                    remaining,
                    lot["quantity"],
                )

                lot["quantity"] -= matched
                remaining -= matched

                if lot["quantity"] <= 0:
                    lots[ticker].pop(0)

    return lots


def calculate_realized_pnl(trades, initial_positions):
    lots = {}

    for ticker, position in initial_positions.items():
        quantity = float(position["quantity"])
        price = float(position["average_price"])

        if quantity > 0:
            lots[ticker] = [{"quantity": quantity, "price": price}]

    realized_pnl = 0.0
    winning_trades = 0
    losing_trades = 0
    largest_win = 0.0
    largest_loss = 0.0
    trade_results = []

    for trade in trades:
        ticker = trade[2]
        direction = trade[3]
        quantity = float(trade[4])
        price = float(trade[5])

        if ticker not in lots:
            lots[ticker] = []

        if direction == "BUY":
            lots[ticker].append({
                "quantity": quantity,
                "price": price,
            })
            continue

        if direction != "SELL":
            continue

        remaining = quantity
        trade_pnl = 0.0
        matched_quantity = 0.0

        while remaining > 0 and lots[ticker]:
            lot = lots[ticker][0]

            matched = min(
                remaining,
                lot["quantity"],
            )

            cost_basis = matched * lot["price"]
            proceeds = matched * price

            trade_pnl += proceeds - cost_basis
            matched_quantity += matched

            lot["quantity"] -= matched
            remaining -= matched

            if lot["quantity"] <= 0:
                lots[ticker].pop(0)

        if matched_quantity == 0:
            continue

        realized_pnl += trade_pnl

        if trade_pnl > 0:
            winning_trades += 1
            largest_win = max(largest_win, trade_pnl)

        elif trade_pnl < 0:
            losing_trades += 1
            largest_loss = min(largest_loss, trade_pnl)

        trade_results.append({
            "ticker": ticker,
            "quantity": matched_quantity,
            "pnl": trade_pnl,
        })

    return {
        "realized_pnl": realized_pnl,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "trade_results": trade_results,
    }


def calculate_unrealized_pnl(trades, initial_positions):
    lots = build_fifo_lots(
        trades,
        initial_positions,
    )

    active_tickers = [
        ticker
        for ticker, ticker_lots in lots.items()
        if ticker_lots
    ]

    if not active_tickers:
        return {
            "unrealized_pnl": 0.0,
            "market_value": 0.0,
            "cost_basis": 0.0,
            "prices": {},
        }

    prices = get_prices(active_tickers)

    market_value = 0.0
    cost_basis = 0.0

    for ticker in active_tickers:
        ticker_lots = lots[ticker]

        current_price = prices.get(ticker)

        if current_price is None:
            current_price = ticker_lots[-1]["price"]

        for lot in ticker_lots:
            quantity = float(lot["quantity"])
            entry_price = float(lot["price"])

            cost_basis += quantity * entry_price
            market_value += quantity * current_price

    return {
        "unrealized_pnl": market_value - cost_basis,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "prices": prices,
    }


def calculate_performance(initial_equity=100_000.00):
    trades = get_trades()
    equity_history = get_equity_history()

    initial_portfolio = load_initial_portfolio()

    initial_cash = float(
        initial_portfolio.get("cash", initial_equity)
    )

    initial_positions = initial_portfolio.get(
        "positions",
        {},
    )

    current_cash, current_positions = load_portfolio()

    if current_cash is None:
        current_cash = initial_cash

    total_trades = len(trades)

    buy_trades = sum(
        1 for trade in trades
        if trade[3] == "BUY"
    )

    sell_trades = sum(
        1 for trade in trades
        if trade[3] == "SELL"
    )

    if equity_history:
        latest = equity_history[-1]

        # Current equity_snapshots schema:
        # id, timestamp, equity
        #
        # get_equity_history() returns:
        # id, timestamp, NULL-as-cash, equity

        current_equity = float(latest[3])

        current_cash = float(
            current_cash
            if current_cash is not None
            else initial_cash
        )

        portfolio_pnl = (
            current_equity - initial_equity
        )

        total_return_pct = (
            portfolio_pnl / initial_equity * 100
            if initial_equity > 0
            else 0.0
        )

    else:
        current_equity = initial_equity
        portfolio_pnl = 0.0
        total_return_pct = 0.0

    realized = calculate_realized_pnl(
        trades,
        initial_positions,
    )

    realized_pnl = realized["realized_pnl"]
    winning_trades = realized["winning_trades"]
    losing_trades = realized["losing_trades"]
    largest_win = realized["largest_win"]
    largest_loss = realized["largest_loss"]

    closed_trades = (
        winning_trades + losing_trades
    )

    win_rate = (
        winning_trades / closed_trades * 100
        if closed_trades > 0
        else 0.0
    )

    unrealized = calculate_unrealized_pnl(
        trades,
        initial_positions,
    )

    unrealized_pnl = unrealized["unrealized_pnl"]
    market_value = unrealized["market_value"]
    cost_basis = unrealized["cost_basis"]
    current_prices = unrealized["prices"]

    total_trading_pnl = (
        realized_pnl + unrealized_pnl
    )

    calculated_return_pct = (
        total_trading_pnl / initial_equity * 100
        if initial_equity > 0
        else 0.0
    )

    equity_values = [
        float(row[3])
        for row in equity_history
        if row[3] is not None
    ]

    high_water_mark = (
        max(initial_equity, max(equity_values))
        if equity_values
        else initial_equity
    )

    max_drawdown_pct = 0.0
    running_peak = initial_equity

    for equity in equity_values:
        running_peak = max(
            running_peak,
            equity,
        )

        if running_peak > 0:
            drawdown = (
                (running_peak - equity)
                / running_peak
                * 100
            )

            max_drawdown_pct = max(
                max_drawdown_pct,
                drawdown,
            )

    current_drawdown_pct = (
        (high_water_mark - current_equity)
        / high_water_mark
        * 100
        if high_water_mark > 0
        else 0.0
    )

    invested_pct = (
        market_value / current_equity * 100
        if current_equity > 0
        else 0.0
    )

    return {
        "initial_equity": initial_equity,
        "current_equity": current_equity,
        "invested_pct": invested_pct,
        "current_cash": current_cash,
        "portfolio_pnl": portfolio_pnl,
        "total_return_pct": total_return_pct,
        "calculated_return_pct": calculated_return_pct,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_trading_pnl": total_trading_pnl,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "total_trades": total_trades,
        "buy_trades": buy_trades,
        "sell_trades": sell_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "closed_trades": closed_trades,
        "win_rate": win_rate,
        "win_rate_pct": win_rate,
        "average_trade_pnl": (
            total_trading_pnl / closed_trades
            if closed_trades > 0
            else 0.0
        ),
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "max_drawdown_pct": max_drawdown_pct,
        "current_drawdown_pct": current_drawdown_pct,
        "high_water_mark": high_water_mark,
        "current_prices": current_prices,
        "equity_history": equity_history,
        "current_positions": current_positions,
    }


def print_performance(initial_equity=100_000.00):
    performance = calculate_performance(initial_equity)

    print()
    print("=" * 60)
    print("EVENTPULSE PERFORMANCE")
    print("=" * 60)
    print(
        f"Initial equity:   ${performance['initial_equity']:,.2f}"
    )
    print(
        f"Current equity:   ${performance['current_equity']:,.2f}"
    )
    print(
        f"Portfolio P/L:    ${performance['portfolio_pnl']:,.2f}"
    )
    print(
        f"Total return:     {performance['total_return_pct']:.2f}%"
    )
    print(
        f"Realized P/L:     ${performance['realized_pnl']:,.2f}"
    )
    print(
        f"Unrealized P/L:   ${performance['unrealized_pnl']:,.2f}"
    )
    print(
        f"Total trading P/L:${performance['total_trading_pnl']:,.2f}"
    )
    print(
        f"Total trades:     {performance['total_trades']}"
    )
    print(
        f"Win rate:         {performance['win_rate']:.2f}%"
    )
    print(
        f"Max drawdown:     {performance['max_drawdown_pct']:.2f}%"
    )
    print("=" * 60)
