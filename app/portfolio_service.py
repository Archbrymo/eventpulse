"""
Canonical EventPulse portfolio persistence and valuation helpers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def normalize_position(position: Any) -> Dict[str, float]:
    if not isinstance(position, dict):
        return {
            "quantity": 0.0,
            "average_price": 0.0,
        }

    return {
        "quantity": float(position.get("quantity", 0.0) or 0.0),
        "average_price": float(
            position.get("average_price", 0.0) or 0.0
        ),
    }


def normalize_portfolio(portfolio: Any) -> Dict[str, Any]:
    portfolio = portfolio if isinstance(portfolio, dict) else {}

    positions = portfolio.get("positions") or {}

    normalized_positions = {}
    for ticker, position in positions.items():
        normalized_positions[str(ticker)] = normalize_position(position)

    return {
        "cash": float(portfolio.get("cash", 0.0) or 0.0),
        "positions": normalized_positions,
        "updated_at": portfolio.get("updated_at")
        or datetime.utcnow().isoformat(),
    }


def cost_basis(portfolio: Dict[str, Any]) -> float:
    portfolio = normalize_portfolio(portfolio)

    return sum(
        p["quantity"] * p["average_price"]
        for p in portfolio["positions"].values()
    )


def mark_to_market(
    portfolio: Dict[str, Any],
    prices: Dict[str, float],
) -> Dict[str, Any]:
    """
    Mark every known position using the freshest supplied market price.

    Falls back to average price only when no current price exists.
    """
    portfolio = normalize_portfolio(portfolio)

    position_value = 0.0
    marked_positions = {}

    for ticker, position in portfolio["positions"].items():
        quantity = position["quantity"]
        average_price = position["average_price"]

        current_price = prices.get(ticker)

        if current_price is None:
            current_price = average_price

        current_price = float(current_price or 0.0)
        market_value = quantity * current_price
        position_value += market_value

        marked_positions[ticker] = {
            **position,
            "current_price": current_price,
            "market_value": market_value,
        }

    cash = portfolio["cash"]

    return {
        **portfolio,
        "positions": marked_positions,
        "position_value": position_value,
        "equity": cash + position_value,
        "valuation_timestamp": datetime.utcnow().isoformat(),
    }
