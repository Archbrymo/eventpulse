from typing import Optional

from .models import AssetSignal

MIN_CONFIDENCE = 0.60

MAX_TRADE_PORTFOLIO_PCT = 0.10
MAX_POSITION_PCT = 0.20
MAX_DAILY_LOSS_PCT = 0.02
MAX_DRAWDOWN_PCT = 0.10


def approve_signal(signal: AssetSignal) -> bool:
    """
    Deterministic gate applied after the LLM decision.
    """

    if signal.direction in ("HOLD", "WAIT"):
        return False

    if signal.confidence < MIN_CONFIDENCE:
        return False

    return True


def portfolio_risk_allowed(
    portfolio_value: float,
    initial_equity: float,
    daily_start_equity: Optional[float] = None,
):
    """
    Check portfolio-level drawdown and daily-loss limits.
    """

    if initial_equity <= 0:
        return False, "Invalid initial equity"

    drawdown_pct = (
        (initial_equity - portfolio_value)
        / initial_equity
    )

    if drawdown_pct >= MAX_DRAWDOWN_PCT:
        return (
            False,
            f"Maximum drawdown exceeded ({drawdown_pct:.2%})",
        )

    if daily_start_equity is not None:

        if daily_start_equity <= 0:
            return False, "Invalid daily starting equity"

        daily_loss_pct = max(
            0.0,
            (daily_start_equity - portfolio_value)
            / daily_start_equity,
        )

        if daily_loss_pct >= MAX_DAILY_LOSS_PCT:
            return (
                False,
                f"Daily loss limit exceeded ({daily_loss_pct:.2%})",
            )

    return True, "Portfolio risk within limits"


def calculate_trade_notional(
    signal: AssetSignal,
    price: float,
    cash: float,
    current_quantity: float,
    portfolio_value: float,
) -> float:
    """
    Calculate permitted trade value in USDT.

    Uses fractional quantities for rTokens.
    """

    if price <= 0:
        return 0.0

    if portfolio_value <= 0:
        return 0.0

    if signal.direction in ("HOLD", "WAIT"):
        return 0.0

    if signal.confidence < MIN_CONFIDENCE:
        return 0.0

    # SELL
    if signal.direction == "SELL":

        if current_quantity <= 0:
            return 0.0

        current_position_value = (
            current_quantity * price
        )

        if signal.confidence >= 0.90:
            sell_fraction = 1.00
        elif signal.confidence >= 0.80:
            sell_fraction = 0.50
        else:
            sell_fraction = 0.25

        return current_position_value * sell_fraction

    # BUY
    if signal.direction == "BUY":

        confidence_factor = min(
            1.0,
            max(
                0.40,
                (signal.confidence - 0.50) / 0.50,
            ),
        )

        max_trade_value = (
            portfolio_value
            * MAX_TRADE_PORTFOLIO_PCT
            * confidence_factor
        )

        current_position_value = (
            current_quantity * price
        )

        max_position_value = (
            portfolio_value * MAX_POSITION_PCT
        )

        remaining_position_capacity = (
            max_position_value
            - current_position_value
        )

        if remaining_position_capacity <= 0:
            return 0.0

        trade_value = min(
            max_trade_value,
            remaining_position_capacity,
            cash,
        )

        return max(0.0, trade_value)

    return 0.0


def calculate_quantity_from_notional(
    notional: float,
    price: float,
) -> float:
    """
    Convert USDT trade value into fractional asset quantity.
    """

    if notional <= 0 or price <= 0:
        return 0.0

    return round(notional / price, 6)
