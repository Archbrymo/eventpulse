"""Canonical EventPulse event-driven paper-trading cycle.

EVENT -> REALITY -> FAST -> EVIDENCE -> QWEN -> RISK -> PAPER -> AUDIT

The dashboard is a presentation layer. It must not reconstruct this
pipeline or call Qwen independently.
"""

from datetime import datetime
import uuid

from app.bitget_universe import (
    get_universe_symbols,
    rank_candidates,
    underlying_ticker,
)
from app.council import analyze_event_with_finalists
from app.database import (
    load_portfolio,
    save_agent_cycle,
    save_portfolio,
    save_qwen_decision,
    save_trade,
)
from app.execution import PaperExecutor
from app.news import get_market_events
from app.risk import (
    approve_signal,
    calculate_quantity_from_notional,
    calculate_trade_notional,
    portfolio_risk_allowed,
)
from app.assets import get_execution_symbol


INITIAL_EQUITY = 100000.0


def _underlying(value):
    try:
        return underlying_ticker(value)
    except Exception:
        value = str(value or "").upper()
        if value.startswith("R"):
            value = value[1:]
        if value.endswith("USDT"):
            value = value[:-4]
        return value


def _price_for_signal(signal, research):
    """Resolve the live Bitget Reality price for a Qwen research ticker."""
    target = str(signal.ticker or "").upper()

    for row in research:
        ticker_data = row.get("ticker_data") or {}

        candidates = {
            str(row.get("ticker") or "").upper(),
            str(row.get("execution_symbol") or "").upper(),
            str(row.get("symbol") or "").upper(),
            str(ticker_data.get("symbol") or "").upper(),
            str(row.get("underlying") or "").upper(),
            str(ticker_data.get("underlying") or "").upper(),
        }

        # Direct symbol/ticker match.
        if target in candidates:
            try:
                return float(
                    ticker_data.get("last")
                    or row.get("last_price")
                    or row.get("price")
                    or 0
                )
            except Exception:
                return 0.0

        # Underlying Reality ticker match.
        underlying_candidates = [
            row.get("ticker"),
            row.get("execution_symbol"),
            row.get("symbol"),
            row.get("underlying"),
            ticker_data.get("symbol"),
            ticker_data.get("underlying"),
        ]

        for candidate in underlying_candidates:
            try:
                if _underlying(candidate).upper() == target:
                    return float(
                        ticker_data.get("last")
                        or row.get("last_price")
                        or row.get("price")
                        or 0
                    )
            except Exception:
                continue

    return 0.0


def _portfolio_equity(portfolio):
    cash = float(portfolio.get("cash", 0.0) or 0.0)
    positions = portfolio.get("positions", {}) or {}

    value = 0.0

    for position in positions.values():
        try:
            value += (
                float(position.get("quantity", 0.0))
                * float(position.get("average_price", 0.0))
            )
        except Exception:
            continue

    return cash + value


def _position_quantity(portfolio, ticker):
    execution_symbol = get_execution_symbol(ticker)
    position = (
        portfolio.get("positions", {})
        .get(execution_symbol)
    )

    if not position:
        return 0.0

    try:
        return float(position.get("quantity", 0.0))
    except Exception:
        return 0.0


def run_event_driven_cycle(execute_paper=False):
    """Run one complete EventPulse cycle.

    execute_paper=False:
        Full analysis/risk path, but no order is submitted.

    execute_paper=True:
        Risk-approved BUY/SELL signals may be sent to PaperExecutor.
        No live exchange execution exists in this function.
    """

    cycle_id = uuid.uuid4().hex[:12]

    result = {
        "cycle_id": cycle_id,
        "timestamp": datetime.utcnow().isoformat(),
        "reality": 0,
        "fast": 0,
        "evidence": 0,
        "qwen": 0,
        "risk": 0,
        "approved": 0,
        "filled": 0,
        "blocked": 0,
        "paper_execution": {
            "attempted": 0,
            "filled": 0,
            "failed": 0,
        },
        "event": None,
        "research": [],
        "signals": [],
        "audit": [],
        "error": None,
        "paper_mode": True,
        "execution_enabled": bool(execute_paper),
    }

    def mark(
        stage,
        status,
        detail="",
        ticker="",
        decision="",
        confidence=None,
    ):
        save_agent_cycle(
            cycle_id=cycle_id,
            stage=stage,
            status=status,
            detail=str(detail or ""),
            ticker=str(ticker or ""),
            decision=str(decision or ""),
            confidence=confidence,
        )

        result["audit"].append({
            "stage": stage,
            "status": status,
            "detail": str(detail or ""),
            "ticker": ticker,
            "decision": decision,
            "confidence": confidence,
        })

    try:
        # --------------------------------------------------------------
        # REALITY
        # --------------------------------------------------------------

        mark(
            "REALITY",
            "STARTED",
            "Discovering live Bitget Reality instruments",
        )

        universe = get_universe_symbols(
            force_refresh=True
        ) or []

        result["reality"] = len(universe)

        mark(
            "REALITY",
            "COMPLETED",
            f"{len(universe)} live instruments",
        )

        # --------------------------------------------------------------
        # FAST
        # --------------------------------------------------------------

        mark(
            "FAST",
            "STARTED",
            "Ranking live candidates",
        )

        fast = rank_candidates(50) or []

        result["fast"] = len(fast)

        mark(
            "FAST",
            "COMPLETED",
            f"{len(fast)} fast candidates",
        )

        # --------------------------------------------------------------
        # PORTFOLIO
        # --------------------------------------------------------------

        cash, positions = load_portfolio()

        portfolio = {
            "cash": float(cash or 0.0),
            "positions": positions or {},
        }

        portfolio_value = _portfolio_equity(portfolio)

        # --------------------------------------------------------------
        # EVIDENCE
        # --------------------------------------------------------------

        mark(
            "EVIDENCE",
            "STARTED",
            "Building evidence pack for top candidates",
        )

        from app.universe_research import research_candidates

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
            mark(
                "QWEN",
                "WAITING",
                "No evidence finalists available",
            )
            return result

        # --------------------------------------------------------------
        # EVENT
        # --------------------------------------------------------------

        researched_tickers = sorted(
            {
                _underlying(
                    row.get("ticker")
                    or row.get("execution_symbol")
                    or row.get("symbol")
                    or ""
                )
                for row in research
                if (
                    row.get("ticker")
                    or row.get("execution_symbol")
                    or row.get("symbol")
                )
            }
        )

        mark(
            "EVENT",
            "STARTED",
            "Reading live market-event stream",
        )

        events = (
            get_market_events(tickers=researched_tickers)
            if researched_tickers
            else []
        )

        if not events:
            events = get_market_events()

        # Market-movement fallback:
        # Bitget Reality evidence itself can become an actionable event.
        # This keeps the autonomous cycle alive when the external news
        # feed returns zero headlines/events.

        if not events:
            market_events = []

            for row in research or []:
                ticker_data = row.get("ticker_data") or {}

                ticker = str(
                    row.get("underlying")
                    or row.get("ticker")
                    or row.get("symbol")
                    or ticker_data.get("underlying")
                    or ""
                ).upper().strip()

                # Reality research can expose the 24h move under several
                # fields depending on the upstream response shape.
                raw_change = (
                    ticker_data.get("change_pct")
                    if ticker_data.get("change_pct") is not None
                    else row.get("change_pct")
                )

                if raw_change is None:
                    raw_change = (
                        ticker_data.get("change")
                        if ticker_data.get("change") is not None
                        else row.get("change")
                    )

                try:
                    change = float(raw_change or 0)
                except (TypeError, ValueError):
                    change = 0.0

                raw_price = (
                    ticker_data.get("last")
                    if ticker_data.get("last") is not None
                    else row.get("price")
                )

                if raw_price is None:
                    raw_price = row.get("last_price")

                try:
                    price = float(raw_price or 0)
                except (TypeError, ValueError):
                    price = 0.0

                # A material Reality move is an event.
                if ticker and price > 0 and abs(change) >= 1.5:
                    market_events.append(
                        {
                            "ticker": ticker,
                            "headline": (
                                f"Reality market move: "
                                f"{ticker} {change:+.2f}%"
                            ),
                            "reason": (
                                "Material 24h price movement detected "
                                "in the Bitget Reality universe."
                            ),
                            "catalyst": (
                                "positive_market_momentum"
                                if change > 0
                                else "negative_market_momentum"
                            ),
                            "relevance": min(
                                1.0,
                                0.50 + abs(change) / 20.0,
                            ),
                            "source": "bitget_reality",
                            "change_pct": change,
                            "price": price,
                        }
                    )

            market_events.sort(
                key=lambda event: abs(
                    float(event.get("change_pct") or 0)
                ),
                reverse=True,
            )

            if market_events:
                events = market_events

                mark(
                    "EVENT",
                    "FALLBACK",
                    market_events[0]["headline"],
                    ticker=market_events[0]["ticker"],
                )

        # Final evidence-only fallback.
        # If the Reality research rows contain valid price data but no
        # usable 24h move, the strongest evidence finalist can still be
        # handed to Qwen. This prevents a temporary news/momentum feed
        # failure from stopping the autonomous agent.

        if not events:
            fallback = None

            for row in research or []:
                ticker_data = row.get("ticker_data") or {}

                ticker = str(
                    row.get("underlying")
                    or row.get("ticker")
                    or row.get("symbol")
                    or ticker_data.get("underlying")
                    or ""
                ).upper().strip()

                try:
                    price = float(
                        ticker_data.get("last")
                        if ticker_data.get("last") is not None
                        else (
                            row.get("price")
                            if row.get("price") is not None
                            else row.get("last_price") or 0
                        )
                    )
                except (TypeError, ValueError):
                    price = 0.0

                if not ticker or price <= 0:
                    continue

                fallback = {
                    "ticker": ticker,
                    "headline": (
                        f"Reality evidence finalist: {ticker}"
                    ),
                    "reason": (
                        "No external news event was available. "
                        "Qwen is evaluating the strongest live "
                        "Bitget Reality evidence finalist."
                    ),
                    "catalyst": "reality_evidence",
                    "relevance": 0.50,
                    "source": "bitget_reality_evidence",
                    "change_pct": 0.0,
                    "price": price,
                }
                break

            if fallback:
                events = [fallback]

                mark(
                    "EVENT",
                    "EVIDENCE_FALLBACK",
                    fallback["headline"],
                    ticker=fallback["ticker"],
                )

        if not events:
            mark(
                "EVENT",
                "WAITING",
                "No actionable live event or Reality evidence finalist returned",
            )
            mark(
                "QWEN",
                "WAITING",
                "No usable event/evidence input available",
            )
            return result

        event = events[0]
        result["event"] = event

        event_text = (
            event.get("headline")
            or event.get("title")
            or str(event)
        )

        mark(
            "EVENT",
            "COMPLETED",
            str(event_text)[:500],
        )

        # --------------------------------------------------------------
        # QWEN
        # --------------------------------------------------------------

        mark(
            "QWEN",
            "STARTED",
            "Calling Qwen investment council",
        )

        decision = analyze_event_with_finalists(
            event=event,
            research_pack=research,
            portfolio_context=portfolio,
        )

        signals = decision.signals or []

        result["signals"] = [
            signal.model_dump()
            for signal in signals
        ]
        result["qwen"] = len(signals)

        for signal in signals:
            price = _price_for_signal(
                signal,
                research,
            )

            save_qwen_decision(
                ticker=signal.ticker,
                decision=str(signal.direction),
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
                decision=str(signal.direction),
                confidence=signal.confidence,
            )

        if not signals:
            mark(
                "QWEN",
                "WAITING",
                "Council returned no signals",
            )
            return result

        # --------------------------------------------------------------
        # RISK
        # --------------------------------------------------------------

        mark(
            "RISK",
            "STARTED",
            "Applying deterministic Python risk controls",
        )

        risk_ok, risk_reason = portfolio_risk_allowed(
            portfolio_value=portfolio_value,
            initial_equity=INITIAL_EQUITY,
            daily_start_equity=INITIAL_EQUITY,
        )

        if not risk_ok:
            result["blocked"] = len(signals)

            mark(
                "RISK",
                "BLOCKED",
                risk_reason,
            )

            return result

        executor = PaperExecutor(portfolio)

        for signal in signals:
            direction = str(signal.direction).upper()

            # Normalize Pydantic Enum values such as DIRECTION.BUY
            # into the plain BUY/SELL strings expected by PaperExecutor.
            if "." in direction:
                direction = direction.split(".")[-1]

            ticker = str(signal.ticker or "").upper()
            confidence = float(signal.confidence or 0.0)

            # Qwen HOLD/WAIT never reaches execution.
            paper_confidence_ok = (
                execute_paper
                and confidence >= 0.40
                and direction in ("BUY", "SELL")
            )

            if not approve_signal(signal) and not paper_confidence_ok:
                result["blocked"] += 1

                mark(
                    "RISK",
                    "BLOCKED",
                    (
                        "Signal failed deterministic confidence/direction gate"
                        if not execute_paper
                        else "Signal failed paper confidence/direction gate"
                    ),
                    ticker=ticker,
                    decision=direction,
                    confidence=confidence,
                )
                continue

            price = _price_for_signal(
                signal,
                research,
            )

            if price <= 0:
                result["blocked"] += 1

                mark(
                    "RISK",
                    "BLOCKED",
                    "No valid Reality execution price",
                    ticker=ticker,
                    decision=direction,
                    confidence=confidence,
                )
                continue

            current_quantity = _position_quantity(
                portfolio,
                ticker,
            )

            # Recalculate equity because previous approved paper
            # fills can change cash/positions during this same cycle.
            current_equity = _portfolio_equity(
                portfolio
            )

            trade_notional = calculate_trade_notional(
                signal=signal,
                price=price,
                cash=float(portfolio.get("cash", 0.0)),
                current_quantity=current_quantity,
                portfolio_value=current_equity,
                min_confidence=0.40 if execute_paper else 0.60,
            )

            quantity = calculate_quantity_from_notional(
                trade_notional,
                price,
            )

            if trade_notional <= 0 or quantity <= 0:
                result["blocked"] += 1

                mark(
                    "RISK",
                    "BLOCKED",
                    "Deterministic position sizing returned zero",
                    ticker=ticker,
                    decision=direction,
                    confidence=confidence,
                )
                continue

            result["risk"] += 1
            result["approved"] += 1

            mark(
                "RISK",
                "APPROVED",
                (
                    f"{direction} {quantity:.6f} {ticker} "
                    f"@ {price:.6f}; "
                    f"notional={trade_notional:.2f}"
                ),
                ticker=ticker,
                decision=direction,
                confidence=confidence,
            )

            if not execute_paper:
                continue

            # ----------------------------------------------------------
            # PAPER EXECUTION
            # ----------------------------------------------------------

            result["paper_execution"]["attempted"] += 1

            mark(
                "EXECUTION",
                "STARTED",
                "Submitting to PaperExecutor",
                ticker=ticker,
                decision=direction,
                confidence=confidence,
            )

            execution = executor.execute(
                ticker=ticker,
                side=direction,
                price=price,
                target_notional=trade_notional,
                quantity=quantity,
            )

            if execution.get("success"):
                filled_quantity = float(
                    execution.get("quantity", quantity)
                )
                filled_price = float(
                    execution.get("price", price)
                )

                execution_symbol = execution.get(
                    "execution_symbol"
                )

                save_trade(
                    ticker=ticker,
                    side=direction,
                    quantity=filled_quantity,
                    price=filled_price,
                    reason=(
                        signal.reasoning
                        or "EventPulse autonomous paper execution"
                    ),
                    execution_symbol=execution_symbol,
                    status="FILLED",
                    confidence=confidence,
                    reasoning=signal.reasoning,
                )

                # Persist the mutated PaperBroker portfolio.
                save_portfolio(
                    portfolio,
                    equity=_portfolio_equity(portfolio),
                )

                result["filled"] += 1
                result["paper_execution"]["filled"] += 1

                mark(
                    "EXECUTION",
                    "FILLED",
                    (
                        f"{direction} {filled_quantity:.6f} "
                        f"{ticker} @ {filled_price:.6f}"
                    ),
                    ticker=ticker,
                    decision=direction,
                    confidence=confidence,
                )

            else:
                result["paper_execution"]["failed"] += 1

                mark(
                    "EXECUTION",
                    "FAILED",
                    str(
                        execution.get("reason")
                        or "Paper execution failed"
                    ),
                    ticker=ticker,
                    decision=direction,
                    confidence=confidence,
                )

        result["paper_execution"]["attempted"] = int(
            result["paper_execution"]["attempted"]
        )

        mark(
            "CYCLE",
            "COMPLETED",
            (
                f"Qwen={result['qwen']} "
                f"approved={result['approved']} "
                f"filled={result['filled']} "
                f"blocked={result['blocked']}"
            ),
        )

        return result

    except Exception as exc:
        result["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

        mark(
            "CYCLE",
            "ERROR",
            result["error"],
        )

        return result
