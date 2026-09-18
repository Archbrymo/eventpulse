import json
import os
import time

from dotenv import load_dotenv

from .models import TradingDecision
from .fundamentals import get_fundamentals
from .valuation import get_valuation
from .market import get_market_data
from .portfolio import get_portfolio_evidence
from .qwen_client import client, MODEL

load_dotenv()



def _parse_json_response(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError(
                f"Qwen did not return valid JSON:\n{text}"
            )

        return json.loads(text[start:end + 1])


def _ask_qwen(prompt, max_attempts=2):
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            print(
                f"Calling Qwen Council "
                f"(attempt {attempt}/{max_attempts})..."
            )

            response = client.responses.create(
                model=MODEL,
                input=prompt,
                max_output_tokens=300,
                reasoning={"effort": "none"},
            )

            output = getattr(
                response,
                "output_text",
                None,
            ) or ""

            print(
                f"Qwen Council response received "
                f"({len(output)} characters)."
            )

            print("Qwen raw output preview:")
            print(repr(output[:1500]))

            if output.strip():
                return output

            print("Qwen returned an empty response.")

            try:
                print("Qwen response object:")
                print(response)
            except Exception:
                pass

        except Exception as exc:
            last_error = exc

            print(
                f"Qwen request failed "
                f"(attempt {attempt}/{max_attempts}): "
                f"{type(exc).__name__}: {exc}"
            )

            if attempt < max_attempts:
                print("Retrying Qwen in 3 seconds...")
                time.sleep(3)

    if last_error:
        raise last_error

    raise ValueError(
        "Qwen returned an empty response after all attempts."
    )


def analyze_ticker(ticker, event, portfolio):
    fundamentals = get_fundamentals(ticker)

    valuation = get_valuation(ticker)

    market = get_market_data(ticker)

    current_price = market.get(
        "current_price",
        0.0,
    )

    portfolio_evidence = get_portfolio_evidence(
        portfolio,
        ticker,
        current_price,
    )

    return build_evidence_package(
        ticker=ticker,
        event=event,
        fundamentals=fundamentals,
        valuation=valuation,
        market=market,
        portfolio=portfolio_evidence,
    )


def analyze_event(event, tickers, portfolio=None):
    if portfolio is None:
        portfolio = {
            "cash": 0.0,
            "positions": {},
        }

    evidence_packages = []

    for ticker in tickers:
        package = analyze_ticker(
            ticker=ticker,
            event=event,
            portfolio=portfolio,
        )

        evidence_packages.append(package)

    council_input = {
        "event": event,
        "assets": evidence_packages,
    }

    prompt = build_council_prompt(
        council_input
    )

    raw_response = _ask_qwen(prompt)

    parsed = _parse_json_response(
        raw_response
    )

    ticker = parsed["ticker"]

    package = next(
        item
        for item in evidence_packages
        if item["ticker"] == ticker
    )

    fundamentals = package["fundamentals"]
    valuation = package["valuation"]
    market = package["market"]
    portfolio_evidence = package["portfolio"]

    signal = {
        "ticker": ticker,
        "direction": parsed["direction"],
        "confidence": parsed["confidence"],
        "reasoning": parsed["reasoning"],
        "catalyst": package["event"].get(
            "reason",
            package["event"].get("headline", "")
        ),
        "fundamental_thesis": (
            f"Revenue growth {fundamentals.get('revenue_growth', 0):.1%}; "
            f"earnings growth {fundamentals.get('earnings_growth', 0):.1%}; "
            f"operating margin {fundamentals.get('operating_margin', 0):.1%}."
        ),
        "valuation_thesis": (
            f"Forward P/E {valuation.get('forward_pe', 0):.1f}; "
            f"PEG approximately {valuation.get('peg_approx', 0):.2f}."
        ),
        "market_thesis": (
            f"Price is {market.get('trend_20', 'UNKNOWN')} and "
            f"{market.get('trend_50', 'UNKNOWN')}."
        ),
        "bull_case": (
            "Catalyst and underlying business strength support "
            "continued upside."
        ),
        "bear_case": (
            "Elevated valuation and adverse catalyst follow-through "
            "could limit upside."
        ),
        "invalidation_condition": (
            "The catalyst fails to improve the underlying thesis "
            "or market/fundamental evidence deteriorates."
        ),
        "expected_horizon": "1-3 months",
        "position_reasoning": (
            f"Current position weight is "
            f"{portfolio_evidence.get('position_weight', 0):.1%}."
        ),
    }

    parsed_decision = {
        "event": event.get(
            "headline",
            str(event),
        ),
        "market_regime": parsed["market_regime"],
        "summary": parsed["summary"],
        "signals": [signal],
    }

    return TradingDecision.model_validate(
        parsed_decision
    )