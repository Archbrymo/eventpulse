from .assets import get_execution_symbol
from .broker import PaperBroker


class PaperExecutor:
    """
    Paper-trading execution adapter.

    Research tickers such as NVDA are automatically converted
    to Bitget execution symbols such as rNVDA.
    """

    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.broker = PaperBroker(portfolio)

    def execute(
        self,
        ticker,
        side,
        price,
        target_notional=None,
        quantity=None,
    ):
        execution_symbol = get_execution_symbol(ticker)

        side = side.upper()

        if side == "BUY":
            result = self.broker.buy(
                ticker=execution_symbol,
                price=price,
                quantity=quantity,
                notional=target_notional,
            )

        elif side == "SELL":
            result = self.broker.sell(
                ticker=execution_symbol,
                price=price,
                quantity=quantity,
                notional=target_notional,
            )

        else:
            return {
                "success": False,
                "reason": f"Unsupported execution side: {side}",
            }

        result["research_ticker"] = ticker
        result["execution_symbol"] = execution_symbol

        return result
