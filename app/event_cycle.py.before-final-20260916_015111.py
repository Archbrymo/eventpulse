
"""Canonical EventPulse event-driven agent cycle.

This module owns the real pipeline:
EVENT -> EVIDENCE -> QWEN -> RISK -> PAPER

The dashboard consumes this module instead of reconstructing the pipeline.
"""

import json
import uuid

from app.database import save_agent_cycle, save_qwen_decision
from app.universe_research import research_candidates
from app.council import analyze_event_with_finalists
from app.bitget_universe import underlying_ticker
from app.news import get_market_events
from app.database import load_portfolio


def _underlying(symbol):
    try:
        return underlying_ticker(symbol)
    except Exception:
        value = str(symbol or "").upper()
        if value.startswith("R"):
            value = value[1:]
        if value.endswith("USDT"):
            value = value[:-4]
        return value


def run_event_driven_cycle():
    cycle_id = uuid.uuid4().hex[:12]

    result = {
        "cycle_id": cycle_id,
        "reality": 0,
        "fast": 0,
        "evidence": 0,
        "qwen": 0,
        "risk": 0,
        "approved": 0,
        "filled": 0,
        "event": None,
        "research": [],
        "signals": [],
        "audit": [],
        "error": None,
    }

    def mark(stage, status, detail="", **kwargs):
        save_agent_cycle(
            cycle_id=cycle_id,
            stage=stage,
            status=status,
            detail=detail,
            **kwargs,
        )
        result["audit"].append({
            "stage": stage,
            "status": status,
            "detail": detail,
            **kwargs,
        })

    try:
        mark("REALITY", "STARTED", "Discovering live Reality universe")

        from app.bitget_universe import get_universe_symbols
        universe = get_universe_symbols(force_refresh=True) or []

        result["reality"] = len(universe)
        mark("REALITY", "COMPLETED", f"{len(universe)} live instruments")

        mark("FAST", "STARTED", "Ranking live candidates")

        from app.bitget_universe import rank_candidates
        fast = rank_candidates(50) or []

        result["fast"] = len(fast)
        mark("FAST", "COMPLETED", f"{len(fast)} candidates")

        cash, positions = load_portfolio()
        portfolio = {
            "cash": float(cash or 0),
            "positions": positions or {},
        }

        mark("EVIDENCE", "STARTED", "Researching top candidates")

        research = research_candidates(
            fast_limit=50,
            research_limit=10,
            portfolio=portfolio,
        ) or []

        result["research"] = research
        result["evidence"] = len(research)

        mark(
            "EVIDENCE",
            "COMPLETED",
            f"{len(research)} evidence finalists",
        )

        if not research:
            mark("QWEN", "WAITING", "No evidence finalists")
            return result

        tickers = tuple(
            sorted(
                set(
                    _underlying(
                        row.get("ticker")
                        or row.get("symbol")
                        or ""
                    )
                    for row in research
                )
            )
        )

        mark("EVENT", "STARTED", "Reading live event stream")

        events = get_market_events(tickers=list(tickers)) if tickers else []
        if not events:
            events = get_market_events()

        if not events:
            mark(
                "EVENT",
                "WAITING",
                "No actionable live event returned",
            )
            mark(
                "QWEN",
                "WAITING",
                "Council requires an actionable event",
            )
            return result

        event = events[0]
        result["event"] = event

        mark(
            "EVENT",
            "COMPLETED",
            str(event.get("headline") or event.get("title") or event)[:500],
        )

        mark("QWEN", "STARTED", "Calling Qwen investment council")

        decision = analyze_event_with_finalists(
            event=event,
            research_pack=research,
            portfolio_context=portfolio,
        )

        signals = decision.signals or []
        result["signals"] = [
            signal.model_dump() for signal in signals
        ]
        result["qwen"] = len(signals)

        for signal in signals:
            price = None
            for row in research:
                if str(row.get("ticker", "")).upper() == str(signal.ticker).upper():
                    price = row.get("last_price")
                    break

            save_qwen_decision(
                ticker=signal.ticker,
                decision=signal.direction,
                confidence=signal.confidence,
                price=price,
                reasoning=signal.reasoning,
                catalyst=signal.catalyst,
                fundamental_thesis=signal.fundamental_thesis,
                valuation_thesis=signal.valuation_thesis,
                market_thesis=signal.market_thesis,
                bull_case=signal.bull_case,
                bear_case=signal.bear_case,
                invalidation_condition=signal.invalidation_condition,
                expected_horizon=signal.expected_horizon,
            )

            mark(
                "QWEN",
                "COMPLETED",
                signal.reasoning,
                ticker=signal.ticker,
                decision=signal.direction,
                confidence=signal.confidence,
            )

        if not signals:
            mark("QWEN", "WAITING", "Council returned no signals")
            return result

        # Risk remains deterministic and separate from Qwen.
        mark("RISK", "STARTED", "Deterministic risk review")

        for signal in signals:
            direction = str(signal.direction).upper()

            # WAIT/HOLD are not executable orders.
            if direction in {"WAIT", "HOLD"}:
                mark(
                    "RISK",
                    "BLOCKED",
                    f"{direction} is non-executable",
                    ticker=signal.ticker,
                    decision=direction,
                    confidence=signal.confidence,
                )
                continue

            result["risk"] += 1

            # Existing paper execution remains the final authority.
            # This cycle deliberately does not bypass the existing risk/execution layer.
            mark(
                "RISK",
                "REVIEWED",
                "Candidate passed council direction gate; existing execution layer required",
                ticker=signal.ticker,
                decision=direction,
                confidence=signal.confidence,
            )

        return result

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        mark("CYCLE", "ERROR", result["error"])
        return result
