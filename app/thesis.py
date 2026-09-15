from datetime import datetime, timezone
import re
from typing import Any, Dict

from .database import get_open_theses, update_thesis


def calculate_directional_return(direction, entry_price, current_price):
    if entry_price <= 0 or current_price <= 0:
        return 0.0

    direction = direction.upper()

    if direction == "SELL":
        return (entry_price / current_price) - 1.0

    return (current_price / entry_price) - 1.0


def parse_horizon(horizon):
    """
    Convert strings such as:
        1-3 months
        1 month
        2 weeks
        5 days

    into:
        minimum_days, maximum_days
    """

    if not horizon:
        return None, None

    text = str(horizon).strip().lower()

    match = re.search(
        r"(\d+)\s*(?:-\s*(\d+))?\s*"
        r"(day|days|week|weeks|month|months)",
        text,
    )

    if not match:
        return None, None

    first = int(match.group(1))
    second = int(match.group(2)) if match.group(2) else first
    unit = match.group(3)

    if "day" in unit:
        multiplier = 1
    elif "week" in unit:
        multiplier = 7
    else:
        multiplier = 30

    return first * multiplier, second * multiplier


def calculate_thesis_age_days(created_at):
    if not created_at:
        return 0.0

    try:
        created = datetime.fromisoformat(str(created_at))

        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        return max(
            0.0,
            (now - created).total_seconds() / 86400.0,
        )

    except (ValueError, TypeError):
        return 0.0


def _evidence_text(evidence):
    parts = []

    for key, value in evidence.items():
        if value is None:
            continue

        if key == "invalidation_condition":
            continue

        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                parts.append(f"{key}.{sub_key}: {sub_value}")
        else:
            parts.append(f"{key}: {value}")

    return " ".join(parts).lower()


def _count_terms(text, terms):
    return sum(1 for term in terms if term in text)


def evaluate_thesis(thesis, current_price, new_evidence):
    direction = str(
        thesis.get("direction", "HOLD")
    ).upper()

    entry_price = float(
        thesis.get("entry_price") or 0.0
    )

    return_pct = calculate_directional_return(
        direction=direction,
        entry_price=entry_price,
        current_price=float(current_price),
    )

    horizon = thesis.get("expected_horizon")

    minimum_days, maximum_days = parse_horizon(
        horizon
    )

    age_days = calculate_thesis_age_days(
        thesis.get("created_at")
    )

    text = _evidence_text(new_evidence)

    positive_terms = [
        "positive",
        "bullish",
        "strong",
        "growth",
        "beat",
        "upside",
        "support",
        "improved",
        "catalyst",
    ]

    negative_terms = [
        "negative",
        "bearish",
        "weak",
        "miss",
        "missed",
        "downside",
        "deteriorated",
        "decline",
        "risk",
        "overvalued",
        "extended",
    ]

    positive_score = _count_terms(
        text,
        positive_terms,
    )

    negative_score = _count_terms(
        text,
        negative_terms,
    )

    evidence_balance = (
        positive_score - negative_score
    )

    minimum_horizon_reached = (
        minimum_days is None
        or age_days >= minimum_days
    )

    maximum_horizon_reached = (
        maximum_days is not None
        and age_days >= maximum_days
    )

    strong_contradiction = False

    if direction == "BUY":
        strong_contradiction = (
            evidence_balance <= -3
        )

    elif direction == "SELL":
        strong_contradiction = (
            evidence_balance >= 3
        )

    elif direction == "HOLD":
        strong_contradiction = (
            evidence_balance <= -3
        )

    # ---------------------------------------------------------
    # Horizon-aware lifecycle
    # ---------------------------------------------------------

    if strong_contradiction:
        status = "INVALIDATED"

        if direction == "BUY":
            reason = (
                "Fresh evidence materially "
                "contradicts the bullish thesis."
            )
        elif direction == "SELL":
            reason = (
                "Fresh evidence materially "
                "contradicts the bearish thesis."
            )
        else:
            reason = (
                "Fresh evidence materially "
                "contradicts the hold thesis."
            )

    elif not minimum_horizon_reached:
        status = "UNRESOLVED"

        reason = (
            f"Thesis horizon not reached "
            f"({age_days:.1f}d elapsed; "
            f"minimum {minimum_days}d). "
            "Continue monitoring."
        )

    elif direction == "HOLD":
        if evidence_balance >= 3:
            status = "VALIDATED"
            reason = (
                "Fresh evidence remains supportive "
                "of the original hold thesis."
            )
        else:
            status = "UNRESOLVED"
            reason = (
                "Fresh evidence remains mixed or "
                "insufficient to resolve the hold thesis."
            )

    elif direction == "BUY":
        if (
            evidence_balance >= 2
            and return_pct > 0
        ):
            status = "VALIDATED"
            reason = (
                "Fresh evidence supports the bullish "
                "thesis and price action is supportive."
            )
        elif maximum_horizon_reached:
            status = "UNRESOLVED"
            reason = (
                "Maximum thesis horizon reached without "
                "enough confirmation to validate the thesis."
            )
        else:
            status = "UNRESOLVED"
            reason = (
                "Fresh evidence does not yet provide "
                "enough confirmation."
            )

    elif direction == "SELL":
        if (
            evidence_balance <= -2
            and return_pct > 0
        ):
            status = "VALIDATED"
            reason = (
                "Fresh evidence supports the bearish "
                "thesis and price action is supportive."
            )
        elif maximum_horizon_reached:
            status = "UNRESOLVED"
            reason = (
                "Maximum thesis horizon reached without "
                "enough confirmation to validate the thesis."
            )
        else:
            status = "UNRESOLVED"
            reason = (
                "Fresh evidence does not yet provide "
                "enough confirmation."
            )

    else:
        status = "UNRESOLVED"
        reason = (
            "The thesis direction is not actionable "
            "enough to resolve automatically."
        )

    return {
        "status": status,
        "reason": reason,
        "direction": direction,
        "entry_price": entry_price,
        "current_price": float(current_price),
        "return_pct": return_pct,
        "positive_score": positive_score,
        "negative_score": negative_score,
        "evidence_balance": evidence_balance,
        "expected_horizon": horizon,
        "age_days": age_days,
        "minimum_horizon_days": minimum_days,
        "maximum_horizon_days": maximum_days,
        "minimum_horizon_reached": minimum_horizon_reached,
        "maximum_horizon_reached": maximum_horizon_reached,
    }


def evaluate_open_theses(
    prices,
    evidence_by_ticker,
):
    theses = get_open_theses()

    results = []

    columns = [
        "id",
        "created_at",
        "ticker",
        "direction",
        "confidence",
        "thesis",
        "catalyst",
        "bull_case",
        "bear_case",
        "invalidation_condition",
        "expected_horizon",
        "entry_price",
        "current_price",
        "return_pct",
        "status",
        "resolved_at",
        "resolution_reason",
    ]

    for thesis_row in theses:
        thesis = dict(
            zip(columns, thesis_row)
        )

        ticker = thesis["ticker"]

        current_price = prices.get(ticker)

        if current_price is None:
            continue

        evidence = evidence_by_ticker.get(
            ticker,
            {},
        )

        result = evaluate_thesis(
            thesis=thesis,
            current_price=current_price,
            new_evidence=evidence,
        )

        result["thesis_id"] = thesis["id"]
        result["ticker"] = ticker

        if result["status"] in (
            "VALIDATED",
            "INVALIDATED",
        ):
            update_thesis(
                thesis_id=thesis["id"],
                current_price=current_price,
                return_pct=result["return_pct"],
                status=result["status"],
                resolution_reason=result["reason"],
            )
        else:
            update_thesis(
                thesis_id=thesis["id"],
                current_price=current_price,
                return_pct=result["return_pct"],
            )

        results.append(result)

    return results
