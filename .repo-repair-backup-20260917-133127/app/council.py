from __future__ import annotations

import json
from typing import Any, Dict, List

from app.models import TradingDecision

from app.qwen_client import client, MODEL


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        text = text[start:end + 1]

    return json.loads(text)


def analyze_event_with_finalists(
    event: Dict[str, Any],
    research_pack: List[Dict[str, Any]],
    portfolio_context: Dict[str, Any] | None = None,
) -> TradingDecision:

    portfolio_context = portfolio_context or {}

    evidence_lines = []

    evidence_lines = []

    for i, item in enumerate(research_pack, 1):
        # Canonical Evidence → Council adapter.
        #
        # Reality research provides:
        #   symbol, underlying, ticker_data, evidence_score, ...
        #
        # The Council prompt consumes a stable enriched schema.
        ticker = str(
            item.get("underlying")
            or item.get("ticker")
            or item.get("symbol")
            or ""
        ).upper()

        execution_symbol = str(
            item.get("execution_symbol")
            or item.get("symbol")
            or ""
        ).upper()

        ticker_data = item.get("ticker_data") or {}

        last_price = float(
            ticker_data.get("last")
            or item.get("last_price")
            or item.get("price")
            or 0.0
        )

        change_24h_pct = float(
            ticker_data.get("change_pct")
            or item.get("change_24h_pct")
            or item.get("change_pct")
            or 0.0
        )

        turnover_24h = float(
            ticker_data.get("quote_volume")
            or item.get("turnover_24h")
            or item.get("quote_volume")
            or 0.0
        )

        bid = float(
            ticker_data.get("bid")
            or item.get("bid")
            or 0.0
        )

        ask = float(
            ticker_data.get("ask")
            or item.get("ask")
            or 0.0
        )

        spread_pct = (
            ((ask - bid) / ((ask + bid) / 2.0)) * 100.0
            if bid > 0 and ask > 0 and ask >= bid
            else 0.0
        )

        fast_score = float(
            item.get("score")
            or item.get("fast_score")
            or 0.0
        )

        evidence_score = float(
            item.get("evidence_score")
            or 0.0
        )

        evidence_breakdown = item.get("evidence_breakdown") or {}

        event_relevant = bool(
            item.get("event_relevant")
            or evidence_breakdown.get("event_relevance", 0)
        )

        fundamentals_text = item.get(
            "fundamentals_text",
            "Fundamental data unavailable.",
        )

        valuation_text = item.get(
            "valuation_text",
            "Valuation data unavailable.",
        )

        market_text = item.get(
            "market_text",
            "Market evidence derived from Bitget Reality.",
        )

        portfolio_text = item.get(
            "portfolio_text",
            "Portfolio context supplied separately.",
        )

        evidence_lines.append(
            f"""
ASSET {i}
Ticker: {ticker}
Execution symbol: {execution_symbol}

BITGET REALITY MARKET EVIDENCE
Price: {last_price}
24h move: {change_24h_pct:+.2f}%
24h turnover: ${turnover_24h:,.0f}
Bid: {bid}
Ask: {ask}
Spread: {spread_pct:.3f}%
Fast screen score: {fast_score}
Evidence score: {evidence_score}
Event relevant: {event_relevant}

Evidence breakdown:
{evidence_breakdown}

FUNDAMENTAL EVIDENCE
Source: Yahoo Finance
{fundamentals_text}

VALUATION EVIDENCE
Source: Yahoo Finance
{valuation_text}

MARKET THESIS
{market_text}

PORTFOLIO CONTEXT
{portfolio_text}
"""
        )
    prompt = f"""
You are the Qwen Investment Council inside EventPulse,
an autonomous event-driven paper-trading system.

Your job is to evaluate the strongest candidates identified
by EventPulse's deterministic research engine.

EVIDENCE HIERARCHY

1. EVENT EVIDENCE
The triggering event and its relevance to the candidate.

2. BITGET REALITY MARKET EVIDENCE
Live/current Reality-market price, 24h movement, turnover,
bid/ask spread, liquidity, and deterministic screening scores.

3. FUNDAMENTAL EVIDENCE
Company fundamentals supplied by Yahoo Finance.
Use these as external research evidence, not as live Bitget data.

4. VALUATION EVIDENCE
Valuation metrics and analyst information supplied by Yahoo Finance.
Use these as contextual evidence, not as guaranteed future outcomes.

5. PORTFOLIO EVIDENCE
Existing positions, cash, concentration, and diversification.

IMPORTANT RULES

- Do NOT invent market, fundamental, valuation, or portfolio data.
- Do NOT claim to have browsed the internet.
- Treat Bitget Reality market data as the authoritative source for current execution-market conditions.
- Treat Yahoo Finance fundamentals and valuation as supplementary external research evidence.
- Never treat Yahoo Finance data as live Bitget execution data.
- If external research appears missing, stale, contradictory, or implausible, discount it rather than guessing.
- Do NOT treat the deterministic shortlist score as an investment recommendation.
- Do NOT assume that a high evidence score means BUY.
- Consider contradictory evidence explicitly.
- A strong event alone is not sufficient for a BUY or SELL.
- Prefer WAIT when evidence is incomplete, stale, contradictory, or synthetic.
- You may choose BUY, SELL, HOLD, or WAIT.
- Confidence must be between 0 and 1.
- Keep reasoning concise and evidence-based.
- Risk sizing is handled separately by deterministic Python.
- Execution is paper-only.
- Never invent a price target, catalyst, financial metric, or valuation metric.
- If a data field is unavailable, treat it as unavailable rather than guessing.
- Consider existing portfolio concentration before recommending a position.
- Prioritize the strongest 1-3 opportunities.

EVENT
Ticker: {event.get("ticker", "")}
Headline: {event.get("headline", "")}
Relevance: {event.get("relevance", 0)}
Catalyst: {event.get("catalyst", "")}
Reason: {event.get("reason", "")}

PORTFOLIO CONTEXT
{portfolio_text}

RESEARCH FINALISTS
{"".join(evidence_lines)}

Return ONLY valid JSON in this exact structure:

{{
  "event": "event headline",
  "market_regime": "BULLISH|BEARISH|MIXED|UNCERTAIN",
  "summary": "short council conclusion",
  "signals": [
    {{
      "ticker": "NVDA",
      "direction": "BUY|SELL|HOLD|WAIT",
      "confidence": 0.0,
      "reasoning": "short evidence-based reasoning",
      "catalyst": "specific catalyst or null",
      "fundamental_thesis": "fundamental view",
      "valuation_thesis": "valuation view",
      "market_thesis": "market/momentum view",
      "bull_case": "bull scenario",
      "bear_case": "bear scenario",
      "invalidation_condition": "what invalidates the thesis",
      "expected_horizon": "intraday|days|weeks|months",
      "position_reasoning": "why this belongs or does not belong in the portfolio"
    }}
  ]
}}

Do not output markdown.
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        max_output_tokens=1800,
        reasoning={"effort": "none"},
    )

    text = response.output_text

    data = _extract_json(text)

    return TradingDecision.model_validate(data)
