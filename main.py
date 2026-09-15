from pathlib import Path
from datetime import sys

from datetime import datetime

from app.agent import analyze_event
from app.universe_research import research_candidates
from app.research_pack import build_research_pack
from app.council import analyze_event_with_finalists

from app.assets import get_execution_symbol
from app.execution import PaperExecutor
from app.database import (
    has_recent_buy,
    get_open_theses,
    init_db,
    load_initial_portfolio,
    get_initial_equity,
    get_daily_start_equity,
    set_daily_start_equity,
    get_daily_start_date,
    set_daily_start_date,
    save_portfolio,
    log_trade,
    log_event,
    log_equity_snapshot,
    create_thesis,
)
from app.market import get_prices
from app.news import get_market_events
from app.thesis import evaluate_open_theses
from app.risk import (
    approve_signal,
    calculate_trade_notional,
    calculate_quantity_from_notional,
    portfolio_risk_allowed,
    MAX_POSITION_PCT,
)


SUPPORTED_TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "TSLA",
    "SPY",
    "QQQ",
]


def load_starting_portfolio():
    """
    Load the saved paper portfolio.
    """
    portfolio = load_initial_portfolio()

    if portfolio is None:
        raise RuntimeError(
            "No initial portfolio found."
        )

    return portfolio


def initialize_daily_risk(portfolio_value):
    """
    Persist the beginning-of-day equity baseline.

    The baseline survives application restarts.
    """
    today = datetime.utcnow().date().isoformat()

    stored_date = get_daily_start_date()
    stored_equity = get_daily_start_equity()

    if stored_date != today or stored_equity is None:
        set_daily_start_date(today)
        set_daily_start_equity(portfolio_value)

        print(
            f"Daily risk baseline initialized: "
            f"{portfolio_value:.2f} USDT"
        )

        return portfolio_value

    return stored_equity


def extract_event_tickers(events):
    """
    Extract unique supported tickers from classified events.
    """
    tickers = []

    for event in events:
        ticker = event.get("ticker")

        if (
            ticker
            and ticker in SUPPORTED_TICKERS
            and ticker not in tickers
        ):
            tickers.append(ticker)

    return tickers


def record_theses(
    decision,
    prices,
    event,
):
    """
    Persist Council decisions as open investment theses.

    The event headline is passed through so the database can
    prevent duplicate open theses for the same event.
    """
    thesis_ids = []

    for signal in decision.signals:
        price = prices.get(signal.ticker)

        if price is None:
            print(
                f"Thesis skipped for {signal.ticker}: "
                "price unavailable."
            )
            continue

        thesis_event_key = (
            f"{str(event.get('ticker', '')).upper()}:"
            f"{str(event.get('headline', '')).strip()}"
        )

        thesis_id = create_thesis(
            ticker=signal.ticker,
            direction=signal.direction.value,
            confidence=signal.confidence,
            thesis=signal.reasoning,
            catalyst=signal.catalyst or "",
            bull_case=signal.bull_case or "",
            bear_case=signal.bear_case or "",
            invalidation_condition=(
                signal.invalidation_condition or ""
            ),
            expected_horizon=(
                signal.expected_horizon or ""
            ),
            entry_price=price,
            event_key=thesis_event_key,
        )

        thesis_ids.append(thesis_id)

        print(
            f"THESIS RECORDED: "
            f"#{thesis_id} "
            f"{signal.ticker} "
            f"{signal.direction.value} "
            f"@ {price:.2f}"
        )

    return thesis_ids

def calculate_portfolio_value(portfolio, prices):
    """
    Calculate current mark-to-market portfolio value.
    """
    cash = float(
        portfolio.get("cash", 0.0)
    )

    position_value = 0.0

    for symbol, position in portfolio.get(
        "positions",
        {},
    ).items():

        ticker = None

        for candidate in SUPPORTED_TICKERS:
            if get_execution_symbol(candidate) == symbol:
                ticker = candidate
                break

        if ticker is None:
            continue

        price = prices.get(ticker)

        if price is None:
            continue

        quantity = float(
            position.get(
                "quantity",
                0.0,
            )
        )

        position_value += quantity * price

    return cash + position_value



def has_open_buy_thesis_for_event(ticker, event_key):
    """
    Return True when this ticker already has an OPEN BUY thesis
    for the exact same event.
    """
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM theses
        WHERE ticker = ?
          AND direction = 'BUY'
          AND status = 'OPEN'
          AND event_key = ?
        LIMIT 1
        """,
        (
            str(ticker),
            str(event_key),
        ),
    )

    exists = cursor.fetchone() is not None
    conn.close()

    return exists



def execute_decisions(
    decision,
    portfolio,
    event_key='',
    pipeline_stats=None,
):
    """
    Apply deterministic Python risk controls to Qwen's decisions
    and execute approved trades through the paper broker.
    """
    tickers = [
        signal.ticker
        for signal in decision.signals
    ]

    # Risk and portfolio valuation require prices for
    # the entire portfolio, not only the current event ticker.
    portfolio_tickers = list(
        dict.fromkeys(
            tickers + SUPPORTED_TICKERS
        )
    )

    prices = get_prices(portfolio_tickers)

    if not prices:
        print(
            "No market prices available. "
            "Execution skipped."
        )
        return portfolio

    portfolio_value = calculate_portfolio_value(
        portfolio,
        prices,
    )

    initial_equity = get_initial_equity()

    if initial_equity is None:
        initial_equity = portfolio_value

    daily_start_equity = initialize_daily_risk(
        portfolio_value
    )

    drawdown_pct = (
        portfolio_value / initial_equity
    ) - 1.0

    daily_pnl_pct = (
        portfolio_value / daily_start_equity
    ) - 1.0

    print()
    print("RISK MONITOR")
    print("-" * 50)

    print(
        f"Initial equity: "
        f"{initial_equity:.2f} USDT"
    )

    print(
        f"Current equity: "
        f"{portfolio_value:.2f} USDT"
    )

    print(
        f"Drawdown: "
        f"{drawdown_pct * 100:.2f}%"
    )

    print(
        f"Daily start equity: "
        f"{daily_start_equity:.2f} USDT"
    )

    print(
        f"Today's P/L: "
        f"{daily_pnl_pct * 100:.2f}%"
    )

    risk_allowed, risk_reason = portfolio_risk_allowed(
        portfolio_value=portfolio_value,
        initial_equity=initial_equity,
        daily_start_equity=daily_start_equity,
    )

    if not risk_allowed:
        print()
        print("PORTFOLIO RISK LIMIT BREACHED")
        print(f"Reason: {risk_reason}")
        print("No new trades will be executed.")
        return portfolio

    print(
        "Portfolio risk within limits"
    )

    executor = PaperExecutor(portfolio)

    for signal in decision.signals:
        ticker = signal.ticker

        print()
        print(
            f"Evaluating {ticker}: "
            f"{signal.direction.value} "
            f"confidence={signal.confidence:.2f}"
        )

        if signal.direction.value in ("HOLD", "WAIT"):
            print(
                f"{ticker} "
                f"{signal.direction.value} "
                f"→ No trade required"
            )
            continue

        if not approve_signal(signal):
            print(
                f"Risk rejected: "
                f"{ticker} "
                f"{signal.direction.value}"
            )
            continue

        # Prevent repeated autonomous accumulation of the same
        # ticker shortly after a filled BUY.
        if (
            signal.direction.value == "BUY"
            and has_recent_buy(ticker, cooldown_minutes=60)
        ):
            print(
                f"RISK BLOCK: {ticker} had a BUY "
                f"within the last 60 minutes."
            )
            continue

        # Event-aware thesis gate:
        # block repeated BUYs for the exact same event,
        # but allow a genuinely new catalyst to generate
        # a fresh thesis.
        if signal.direction.value == "BUY":
            if has_open_buy_thesis_for_event(
                ticker,
                event_key,
            ): 
                print(
                    f"RISK BLOCK: {ticker} already has "
                    "an OPEN BUY thesis for this event."
                )
                continue

        price = prices.get(ticker)

        if price is None:
            print(
                f"Execution skipped for {ticker}: "
                "price unavailable."
            )
            continue

        execution_symbol = get_execution_symbol(
            ticker
        )

        current_position = portfolio.get(
            "positions",
            {},
        ).get(
            execution_symbol,
            {},
        )

        current_quantity = float(
            current_position.get(
                "quantity",
                0.0,
            )
        )

        current_position_value = (
            current_quantity * price
        )

        # Hard execution guard: never allow a BUY to
        # push a position above the maximum portfolio weight.
        if signal.direction.value == "BUY":
            max_position_value = (
                portfolio_value * MAX_POSITION_PCT
            )

            if current_position_value >= max_position_value:
                print(
                    f"RISK BLOCK: {ticker} already at "
                    f"max position "
                    f"({current_position_value:.2f} / "
                    f"{max_position_value:.2f} USDT)"
                )
                continue

        notional = calculate_trade_notional(
            signal=signal,
            price=price,
            portfolio_value=portfolio_value,
            cash=float(
                portfolio.get(
                    "cash",
                    0.0,
                )
            ),
            current_quantity=current_quantity,
        )

        if notional <= 0:
            print(
                f"No trade required for "
                f"{ticker}."
            )
            continue

        quantity = calculate_quantity_from_notional(
            notional=notional,
            price=price,
        )

        if quantity <= 0:
            print(
                f"Quantity calculated as zero "
                f"for {ticker}."
            )
            continue

        try:
            result = executor.execute(
                ticker=ticker,
                side=signal.direction.value,
                price=price,
                quantity=quantity,
                target_notional=notional,
            )

        except Exception as exc:
            print(
                f"Execution error for {ticker}: "
                f"{exc}"
            )
            continue

        if not result or not result.get("success", False):
            print(
                f"Execution rejected for {ticker}: "
                f"{result.get('reason', 'unknown execution failure') if result else 'no execution result'}"
            )
            continue

        log_trade(
            ticker=ticker,
            side=signal.direction.value,
            quantity=quantity,
            price=price,
            notional=notional,
            reason=signal.reasoning,
            execution_symbol=result.get("execution_symbol"),
        )

        print(
            f"EXECUTED: "
            f"{signal.direction.value} "
            f"{quantity:.6f} "
            f"{ticker} "
            f"@ {price:.2f}"
        )

    return portfolio


def print_decision(decision):
    """
    Display the Investment Council decision.
    """
    print()
    print("COUNCIL DECISION")
    print("=" * 60)

    print(
        f"Event: {decision.event}"
    )

    print(
        f"Market regime: "
        f"{decision.market_regime}"
    )

    print()
    print(
        f"Summary: {decision.summary}"
    )

    print()

    for signal in decision.signals:
        print(
            f"{signal.ticker} "
            f"{signal.direction.value} "
            f"confidence={signal.confidence:.2f}"
        )

        print(
            f"  Reasoning: "
            f"{signal.reasoning}"
        )

        if signal.catalyst:
            print(
                f"  Catalyst: "
                f"{signal.catalyst}"
            )

        if signal.fundamental_thesis:
            print(
                f"  Fundamentals: "
                f"{signal.fundamental_thesis}"
            )

        if signal.valuation_thesis:
            print(
                f"  Valuation: "
                f"{signal.valuation_thesis}"
            )

        if signal.market_thesis:
            print(
                f"  Market: "
                f"{signal.market_thesis}"
            )

        if signal.bull_case:
            print(
                f"  Bull case: "
                f"{signal.bull_case}"
            )

        if signal.bear_case:
            print(
                f"  Bear case: "
                f"{signal.bear_case}"
            )

        if signal.invalidation_condition:
            print(
                f"  Invalidation: "
                f"{signal.invalidation_condition}"
            )

        if signal.expected_horizon:
            print(
                f"  Horizon: "
                f"{signal.expected_horizon}"
            )

        if signal.position_reasoning:
            print(
                f"  Position: "
                f"{signal.position_reasoning}"
            )

        print()


def print_portfolio(portfolio):
    """
    Display final paper portfolio.
    """
    print()
    print("FINAL PAPER PORTFOLIO")
    print("=" * 60)

    print(
        f"Cash: "
        f"{portfolio.get('cash', 0.0):.2f} USDT"
    )

    print()

    for symbol, position in portfolio.get(
        "positions",
        {},
    ).items():
        quantity = float(
            position.get(
                "quantity",
                0.0,
            )
        )

        average_price = float(
            position.get(
                "average_price",
                0.0,
            )
        )

        print(
            f"{symbol}: "
            f"{quantity:.6f} "
            f"@ avg {average_price:.2f}"
        )


def main():
    print()
    print("=" * 60)
    print(
        "EVENTPULSE AUTONOMOUS "
        "EVENT-DRIVEN TRADING AGENT"
    )
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Initialize database
    # ---------------------------------------------------------

    init_db()

    # ---------------------------------------------------------
    # 2. Load paper portfolio
    # ---------------------------------------------------------

    portfolio = load_starting_portfolio()

    print()
    print("Portfolio loaded.")

    # ---------------------------------------------------------
    # 3. Detect actionable events
    # ---------------------------------------------------------

    test_event_mode = "--test-event" in sys.argv
    dry_run_mode = "--dry-run" in sys.argv

    print()
    print("EVENT INTELLIGENCE")
    print("-" * 50)

    if test_event_mode:
        events = [
            {
                "ticker": "NVDA",
                "headline": (
                    "TEST EVENT: AI demand outlook "
                    "drives semiconductor volatility"
                ),
                "relevance": 0.90,
                "catalyst": "positive",
                "reason": (
                    "Synthetic demonstration event "
                    "for the autonomous trading pipeline."
                ),
            }
        ]

        print("TEST EVENT MODE ENABLED")
        print("Using synthetic NVDA catalyst.")
    else:
        events = get_market_events()

    if not events:
        print(
            "No actionable market events detected."
        )
        return

    # ---------------------------------------------------------
    # 4. Process the strongest event
    #
    # We currently send one event to the Council because
    # agent.py's analyze_event() is designed around a single
    # event object.
    # ---------------------------------------------------------

    event = events[0]

    ticker = event.get(
        "ticker",
        "UNKNOWN",
    )

    headline = event.get(
        "headline",
        "",
    )

    relevance = float(
        event.get(
            "relevance",
            0.0,
        )
    )

    catalyst = event.get(
        "catalyst",
        "mixed",
    )

    reason = event.get(
        "reason",
        "",
    )

    print()
    print("ACTIONABLE EVENT")
    print(
        f"[{ticker}] {headline}"
    )

    print(
        f"  Relevance: "
        f"{relevance * 100:.0f}%"
    )

    print(
        f"  Catalyst: "
        f"{catalyst}"
    )

    print(
        f"  Reason: "
        f"{reason}"
    )

    # ---------------------------------------------------------
    # 5. Persist event
    # ---------------------------------------------------------

    try:
        log_event(
            title=headline,
            summary=reason,
            source="Yahoo Finance / Qwen Event Intelligence",
        )
    except Exception as exc:
        print(
            f"Event logging warning: "
            f"{exc}"
        )

    # ---------------------------------------------------------
    # 6. Autonomous Reality research universe
    # ---------------------------------------------------------

    research_event = {
        "ticker": ticker,
        "headline": headline,
        "relevance": relevance,
        "catalyst": catalyst,
        "reason": reason,
    }

    research_portfolio = {
        "positions": portfolio.get("positions", {}),
    }

    try:
        finalists = research_candidates(
            fast_limit=50,
            research_limit=10,
            event=research_event,
            portfolio=research_portfolio,
        )

    except Exception as exc:
        import traceback

        print()
        print("RESEARCH UNIVERSE ERROR")
        print(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        return

    if not finalists:
        print()
        print("No Reality assets survived research screening.")
        return

    print()
    print("==============================================")
    print("AUTONOMOUS EVENTPULSE RESEARCH UNIVERSE")
    print("==============================================")
    print("1173+ Reality instruments")
    print("        ↓")
    print("50 deterministic market candidates")
    print("        ↓")
    print(f"{len(finalists)} evidence finalists")
    print("        ↓")
    print("Qwen Investment Council")
    print()

    for i, candidate in enumerate(finalists, 1):
        ticker_data = candidate.get("ticker_data", {})

        price = float(ticker_data.get("last", 0.0))
        change_pct = float(ticker_data.get("change_pct", 0.0))
        quote_volume = float(ticker_data.get("quote_volume", 0.0))
        bid = float(ticker_data.get("bid", 0.0))
        ask = float(ticker_data.get("ask", 0.0))

        spread_pct = (
            ((ask - bid) / price) * 100.0
            if price > 0
            else 0.0
        )

        event_relevant = (
            candidate["underlying"].upper()
            == ticker.upper()
        )

        print(
            f"{i}. {candidate['underlying']} "
            f"({candidate['symbol']})"
        )
        print(
            f"   Price: {price:.4f}"
        )
        print(
            f"   24h move: "
            f"{change_pct:+.2f}%"
        )
        print(
            f"   24h turnover: "
            f"${quote_volume:,.0f}"
        )
        print(
            f"   Spread: "
            f"{spread_pct:.3f}%"
        )
        print(
            f"   Fast score: "
            f"{float(candidate['score']):.1f}"
        )
        print(
            f"   Evidence score: "
            f"{float(candidate['evidence_score']):.1f}"
        )
        print(
            f"   Event relevant: "
            f"{event_relevant}"
        )
        print()

    # ---------------------------------------------------------
    # Save live pipeline state for the dashboard
    # ---------------------------------------------------------
    import json

    pipeline_snapshot = {
        "timestamp": datetime.now().isoformat(),
        "reality_universe": 1173,
        "fast_screen": 50,
        "evidence_research": len(finalists),
        "finalists": [
            {
                "ticker": str(candidate.get("underlying", "")),
                "execution_symbol": str(candidate.get("symbol", "")),
                "fast_score": float(candidate.get("score", 0.0)),
                "evidence_score": float(
                    candidate.get("evidence_score", 0.0)
                ),
                "last_price": float(
                    candidate.get("ticker_data", {}).get("last", 0.0)
                ),
                "change_24h_pct": float(
                    candidate.get("ticker_data", {}).get(
                        "change_pct", 0.0
                    )
                ),
                "turnover_24h": float(
                    candidate.get("ticker_data", {}).get(
                        "quote_volume", 0.0
                    )
                ),
            }
            for candidate in finalists
        ],
        "qwen_council": len(finalists),
    }

    Path(".eventpulse_pipeline.json").write_text(
        json.dumps(
            pipeline_snapshot,
            indent=2,
        )
    )

    print()
    print("DASHBOARD PIPELINE SNAPSHOT SAVED")
    print(
        f"1173 Reality → 50 screened → "
        f"{len(finalists)} researched → Qwen Council"
    )

    # ---------------------------------------------------------
    # 7. Build compact evidence pack
    # ---------------------------------------------------------

    research_pack = build_research_pack(
        finalists,
        event=research_event,
    )

    # Council considers the entire finalist set rather than
    # only the ticker named by the news event.
    finalist_tickers = [
        candidate["underlying"]
        for candidate in finalists
    ]

    # ---------------------------------------------------------
    # 8. Qwen Investment Council
    # ---------------------------------------------------------

    try:
        decision = analyze_event_with_finalists(
            event=research_event,
            research_pack=research_pack,
            portfolio_context={
                "cash": portfolio.get("cash", 0.0),
                "positions": portfolio.get("positions", {}),
            },
        )

        # Persist actual Qwen council direction counts.
        decision_counts = {
            "BUY": 0,
            "SELL": 0,
            "HOLD": 0,
            "WAIT": 0,
        }

        for council_signal in getattr(
            decision,
            "signals",
            [],
        ):
            direction = getattr(
                council_signal,
                "direction",
                "",
            )

            direction = getattr(
                direction,
                "value",
                str(direction),
            ).upper()

            if direction in decision_counts:
                decision_counts[direction] += 1

        pipeline_file = Path(".eventpulse_pipeline.json")

        try:
            pipeline_snapshot = json.loads(
                pipeline_file.read_text()
            )
        except Exception:
            pipeline_snapshot = {}

        pipeline_snapshot["decision_counts"] = decision_counts
        pipeline_snapshot["qwen_council"] = len(
            getattr(decision, "signals", [])
        )

        pipeline_file.write_text(
            json.dumps(
                pipeline_snapshot,
                indent=2,
            )
        )

        print()
        print("QWEN PIPELINE COUNTS")
        print(
            f"BUY={decision_counts['BUY']}  "
            f"SELL={decision_counts['SELL']}  "
            f"HOLD={decision_counts['HOLD']}  "
            f"WAIT={decision_counts['WAIT']}"
        )

    except Exception as exc:
        import traceback

        print()
        print("QWEN COUNCIL ERROR")
        print(f"{type(exc).__name__}: {exc}")
        print()
        print("FULL TRACEBACK")
        traceback.print_exc()
        return

    # Use the finalist universe for downstream price lookup.
    event_tickers = finalist_tickers
    # ---------------------------------------------------------
    # 8. Display Council decision
    # ---------------------------------------------------------

    print_decision(
        decision
    )

    # ---------------------------------------------------------
    # 9. Record investment theses
    # ---------------------------------------------------------

    prices = get_prices(
        event_tickers
    )

    print()
    print("THESIS TRACKING")
    print("-" * 50)

    thesis_ids = record_theses(
        decision,
        prices,
        event,
    )

    print(
        f"Recorded "
        f"{len(thesis_ids)} "
        f"investment thesis(es)."
    )

    # ---------------------------------------------------------
    # 10. Risk + paper execution
    # ---------------------------------------------------------

    if dry_run_mode:
        print()
        print("DRY-RUN MODE")
        print("-" * 50)
        print("Qwen decision and thesis recorded.")
        print("Risk/execution step SKIPPED.")
        print("No paper trade created.")
        return

    event_key = (
        f"{str(event.get('ticker', '')).upper()}:"
        f"{str(event.get('headline', '')).strip()}"
    )

    pipeline_execution = {}

    portfolio = execute_decisions(
        decision,
        portfolio,
        event_key=event_key,
        pipeline_stats=pipeline_execution,
    )

    # Persist actual risk and paper-execution outcomes.
    pipeline_file = Path(".eventpulse_pipeline.json")

    try:
        pipeline_snapshot = json.loads(
            pipeline_file.read_text()
        )
    except Exception:
        pipeline_snapshot = {}

    pipeline_snapshot["risk"] = {
        "reviewed": int(
            pipeline_execution.get("risk_reviewed", 0)
        ),
        "approved": int(
            pipeline_execution.get("risk_approved", 0)
        ),
        "blocked": int(
            pipeline_execution.get("risk_blocked", 0)
        ),
    }

    pipeline_snapshot["paper_execution"] = {
        "attempted": int(
            pipeline_execution.get(
                "paper_orders_attempted",
                0,
            )
        ),
        "filled": int(
            pipeline_execution.get(
                "paper_execution_filled",
                0,
            )
        ),
        "failed": int(
            pipeline_execution.get(
                "paper_execution_failed",
                0,
            )
        ),
    }

    pipeline_file.write_text(
        json.dumps(
            pipeline_snapshot,
            indent=2,
        )
    )

    print()
    print("RISK / EXECUTION PIPELINE")
    print(
        f"Risk reviewed: "
        f"{pipeline_execution.get('risk_reviewed', 0)}"
    )
    print(
        f"Risk approved: "
        f"{pipeline_execution.get('risk_approved', 0)}"
    )
    print(
        f"Risk blocked: "
        f"{pipeline_execution.get('risk_blocked', 0)}"
    )
    print(
        f"Paper filled: "
        f"{pipeline_execution.get('paper_execution_filled', 0)}"
    )

    # ---------------------------------------------------------
    # 12. Calculate final equity
    # ---------------------------------------------------------

    final_prices = get_prices(
        SUPPORTED_TICKERS
    )

    final_equity = calculate_portfolio_value(
        portfolio,
        final_prices,
    )

    # ---------------------------------------------------------
    # 13. Persist mark-to-market portfolio snapshot
    # ---------------------------------------------------------

    save_portfolio(
        portfolio=portfolio,
        equity=final_equity,
    )

    # ---------------------------------------------------------
    # 13. Evaluate open investment theses
    # ---------------------------------------------------------

    evidence_by_ticker = {}

    for signal in decision.signals:
        evidence_by_ticker[signal.ticker] = {
            "event": signal.catalyst or "",
            "summary": (
                signal.reasoning
                or decision.summary
                or ""
            ),
            "fundamentals": signal.fundamental_thesis or "",
            "valuation": signal.valuation_thesis or "",
            "market": signal.market_thesis or "",
            "bull_case": signal.bull_case or "",
            "bear_case": signal.bear_case or "",
            "invalidation_condition": (
                signal.invalidation_condition or ""
            ),
            "expected_horizon": (
                signal.expected_horizon or ""
            ),
            "position_reasoning": (
                signal.position_reasoning or ""
            ),
            "decision": signal.direction.value,
            "confidence": signal.confidence,
        }

    thesis_results = evaluate_open_theses(
        prices=final_prices,
        evidence_by_ticker=evidence_by_ticker,
    )

    if thesis_results:
        print()
        print("THESIS EVALUATION")
        print("-" * 50)

        for result in thesis_results:
            print(
                f"#{result['thesis_id']} "
                f"{result['ticker']} "
                f"{result['status']} "
                f"return={result['return_pct']:.2%}"
            )
            print(
                f"  Reason: {result['reason']}"
            )

    # ---------------------------------------------------------
    # 14. Save equity snapshot
    # ---------------------------------------------------------

    try:
        log_equity_snapshot(
            equity=final_equity,
            cash=float(portfolio.get("cash", 0.0)),
        )
    except Exception as exc:
        print(
            f"Equity snapshot warning: "
            f"{exc}"
        )

    # ---------------------------------------------------------
    # 14. Final report
    # ---------------------------------------------------------

    print_portfolio(
        portfolio
    )

    print()
    print(
        f"Estimated portfolio equity: "
        f"{final_equity:.2f} USDT"
    )

    print()
    print("=" * 60)
    print("EVENTPULSE RUN COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
