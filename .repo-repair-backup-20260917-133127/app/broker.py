from datetime import datetime


class PaperBroker:

    def __init__(self, portfolio):
        self.portfolio = portfolio

    def buy(self, ticker, price, quantity=None, notional=None):
        """
        Buy an asset using either:
        - quantity
        - USDT notional
        """

        if price <= 0:
            return {
                "success": False,
                "reason": "Invalid price"
            }

        if notional is not None:
            quantity = notional / price

        if quantity is None or quantity <= 0:
            return {
                "success": False,
                "reason": "Invalid quantity"
            }

        quantity = round(float(quantity), 6)
        price = float(price)

        cost = quantity * price

        cash = self.portfolio["cash"]

        if cost > cash:
            return {
                "success": False,
                "reason": "Insufficient USDT"
            }

        positions = self.portfolio.setdefault("positions", {})

        existing = positions.get(ticker)

        if existing is None:

            positions[ticker] = {
                "quantity": quantity,
                "average_price": price
            }

        else:

            old_quantity = float(existing["quantity"])
            old_average = float(existing["average_price"])

            new_quantity = old_quantity + quantity

            new_average = (
                (old_quantity * old_average) +
                (quantity * price)
            ) / new_quantity

            positions[ticker] = {
                "quantity": new_quantity,
                "average_price": new_average
            }

        self.portfolio["cash"] -= cost

        return {
            "success": True,
            "side": "BUY",
            "ticker": ticker,
            "quantity": quantity,
            "price": price,
            "value": cost,
            "timestamp": datetime.utcnow().isoformat()
        }

    def sell(self, ticker, price, quantity=None, notional=None):
        """
        Sell an asset using either:
        - quantity
        - USDT notional
        """

        if price <= 0:
            return {
                "success": False,
                "reason": "Invalid price"
            }

        positions = self.portfolio.setdefault("positions", {})

        if ticker not in positions:
            return {
                "success": False,
                "reason": f"No position in {ticker}"
            }

        current_quantity = float(
            positions[ticker]["quantity"]
        )

        if notional is not None:
            quantity = notional / price

        if quantity is None or quantity <= 0:
            return {
                "success": False,
                "reason": "Invalid quantity"
            }

        quantity = round(float(quantity), 6)
        price = float(price)

        if quantity > current_quantity + 0.000001:
            return {
                "success": False,
                "reason": "Insufficient position"
            }

        value = quantity * price

        new_quantity = current_quantity - quantity

        if new_quantity <= 0.000001:
            del positions[ticker]
        else:
            positions[ticker]["quantity"] = new_quantity

        self.portfolio["cash"] += value

        return {
            "success": True,
            "side": "SELL",
            "ticker": ticker,
            "quantity": quantity,
            "price": price,
            "value": value,
            "timestamp": datetime.utcnow().isoformat()
        }
