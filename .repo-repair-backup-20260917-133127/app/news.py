import json
import os
import time

import yfinance as yf
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


MODEL = "qwen3.8-max"

QWEN_API_KEY = os.getenv("BITGET_QWEN_API_KEY")

if not QWEN_API_KEY:
    raise RuntimeError(
        "BITGET_QWEN_API_KEY is missing. "
        "Check your .env file."
    )


client = OpenAI(
    api_key=QWEN_API_KEY,
    base_url="https://hackathon.bitgetops.com/v1",
)


DEFAULT_TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "TSLA",
    "SPY",
    "QQQ",
]


def get_news(ticker, limit=5):
    try:
        ticker_obj = yf.Ticker(ticker)
        news = ticker_obj.news or []

        results = []

        for item in news[:limit]:
            content = item.get("content", {})

            title = (
                content.get("title")
                or item.get("title")
                or ""
            )

            if not title:
                continue

            publisher = (
                content.get("provider", {})
                .get("displayName")
                or item.get("publisher")
                or ""
            )

            published = (
                content.get("pubDate")
                or item.get("providerPublishTime")
                or ""
            )

            url = (
                content.get("canonicalUrl", {})
                .get("url")
                or item.get("link")
                or ""
            )

            results.append(
                {
                    "ticker": ticker,
                    "title": title,
                    "publisher": publisher,
                    "published": published,
                    "url": url,
                }
            )

        return results

    except Exception as exc:
        print(
            f"News collection failed for {ticker}: {exc}"
        )
        return []


def collect_raw_headlines(tickers=None, limit_per_ticker=5):
    tickers = tickers or DEFAULT_TICKERS

    headlines = []

    for ticker in tickers:
        headlines.extend(
            get_news(
                ticker=ticker,
                limit=limit_per_ticker,
            )
        )

    print(
        f"Collected {len(headlines)} raw headlines."
    )

    return headlines


def _deduplicate_headlines(headlines):
    seen = set()
    results = []

    for item in headlines:
        title = str(
            item.get("title", "")
        ).strip()

        key = title.lower()

        if not key or key in seen:
            continue

        seen.add(key)
        results.append(item)

    return results


def _deterministic_candidates(headlines):
    catalyst_terms = [
        "earnings",
        "earnings report",
        "earnings results",
        "revenue",
        "profit",
        "guidance",
        "forecast",
        "outlook",
        "acquisition",
        "merger",
        "deal",
        "partnership",
        "launch",
        "product",
        "iphone",
        "ai",
        "artificial intelligence",
        "chip",
        "chips",
        "antitrust",
        "regulation",
        "regulatory",
        "lawsuit",
        "investigation",
        "approval",
        "fda",
        "tariff",
        "trade",
        "buyback",
        "dividend",
        "downgrade",
        "upgrade",
        "price target",
        "analyst",
        "ceo",
        "cfo",
        "layoff",
        "restructuring",
    ]

    hard_event_terms = [
        "earnings",
        "guidance",
        "acquisition",
        "merger",
        "deal",
        "partnership",
        "antitrust",
        "regulation",
        "regulatory",
        "lawsuit",
        "investigation",
        "approval",
        "fda",
        "tariff",
        "trade",
        "buyback",
        "dividend",
        "ceo",
        "cfo",
    ]

    weak_terms = [
        "stock",
        "shares",
        "market",
        "investors",
        "wall street",
        "price",
        "trading",
    ]

    candidates = []

    for item in headlines:
        title = str(
            item.get("title", "")
        ).strip()

        lower_title = title.lower()

        catalyst_hits = sum(
            term in lower_title
            for term in catalyst_terms
        )

        hard_hits = sum(
            term in lower_title
            for term in hard_event_terms
        )

        weak_hits = sum(
            term in lower_title
            for term in weak_terms
        )

        if catalyst_hits == 0:
            continue

        if hard_hits == 0 and weak_hits == 0:
            continue

        candidate = dict(item)
        candidate["catalyst_hits"] = catalyst_hits
        candidate["hard_hits"] = hard_hits

        candidates.append(candidate)

    candidates.sort(
        key=lambda x: (
            x["hard_hits"],
            x["catalyst_hits"],
        ),
        reverse=True,
    )

    candidates = candidates[:15]

    print(
        "Deterministic catalyst candidates: "
        f"{len(candidates)}"
    )

    return candidates


def _parse_json_array(text):
    text = (text or "").strip()

    if not text:
        return []

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1:
        return []

    try:
        value = json.loads(
            text[start:end + 1]
        )

        return value if isinstance(
            value,
            list,
        ) else []

    except Exception:
        return []


def classify_market_events(candidates):
    if not candidates:
        return []

    compact_candidates = []

    for item in candidates:
        compact_candidates.append(
            {
                "ticker": item.get("ticker"),
                "title": item.get("title"),
                "publisher": item.get("publisher"),
                "published": item.get("published"),
            }
        )

    prompt = f"""
You are the event-intelligence classifier for EventPulse.

Identify only potentially trade-relevant U.S. stock events.

A relevant event should have a plausible material effect on:
- earnings
- revenue
- margins
- guidance
- products
- regulation
- litigation
- acquisitions
- partnerships
- management
- major analyst changes
- major macro exposure

Ignore generic market commentary, routine price movement,
technical analysis, and low-information opinion pieces.

Return ONLY a JSON array.

Each selected item must have exactly:

{{
  "ticker": "AAPL",
  "headline": "headline",
  "relevance": 0.0,
  "catalyst": "positive",
  "reason": "short reason"
}}

Rules:
- relevance must be between 0 and 1
- catalyst must be one of:
  positive, negative, mixed, neutral
- include only events with relevance >= 0.50
- do not invent facts
- keep reason short

CANDIDATES:
{json.dumps(compact_candidates, separators=(",", ":"))}
"""

    for attempt in range(2):
        try:
            response = client.responses.create(
                model=MODEL,
                input=prompt,
                max_output_tokens=500,
                reasoning={"effort": "none"},
            )

            raw = getattr(
                response,
                "output_text",
                "",
            )

            parsed = _parse_json_array(raw)

            if parsed:
                valid = []

                valid_tickers = {
                    item.get("ticker")
                    for item in candidates
                }

                for item in parsed:
                    if not isinstance(item, dict):
                        continue

                    ticker = item.get("ticker")
                    headline = item.get("headline")

                    try:
                        relevance = float(
                            item.get("relevance", 0)
                        )
                    except Exception:
                        relevance = 0.0

                    catalyst = str(
                        item.get(
                            "catalyst",
                            "neutral",
                        )
                    ).lower()

                    reason = str(
                        item.get(
                            "reason",
                            "",
                        )
                    ).strip()

                    if ticker not in valid_tickers:
                        continue

                    if not headline:
                        continue

                    if relevance < 0.50:
                        continue

                    if catalyst not in {
                        "positive",
                        "negative",
                        "mixed",
                        "neutral",
                    }:
                        catalyst = "neutral"

                    valid.append(
                        {
                            "ticker": ticker,
                            "headline": str(
                                headline
                            ).strip(),
                            "relevance": min(
                                1.0,
                                max(
                                    0.0,
                                    relevance,
                                ),
                            ),
                            "catalyst": catalyst,
                            "reason": reason,
                        }
                    )

                return valid

        except Exception as exc:
            print(
                f"Event classifier attempt "
                f"{attempt + 1}/2 failed: {exc}"
            )

            if attempt == 0:
                time.sleep(1)

    return []


def filter_market_events(events):
    filtered = []

    for event in events:
        relevance = float(
            event.get("relevance", 0.0)
        )

        if relevance < 0.50:
            continue

        filtered.append(event)

    print(
        f"Selected {len(filtered)} relevant events."
    )

    return filtered


def build_market_event(event):
    return {
        "ticker": event.get("ticker"),
        "headline": event.get("headline"),
        "relevance": float(
            event.get("relevance", 0.0)
        ),
        "catalyst": event.get(
            "catalyst",
            "neutral",
        ),
        "reason": event.get(
            "reason",
            "",
        ),
    }


def get_market_events(tickers=None):
    raw = collect_raw_headlines(
        tickers=tickers
    )

    raw = _deduplicate_headlines(raw)

    candidates = _deterministic_candidates(
        raw
    )

    classified = classify_market_events(
        candidates
    )

    filtered = filter_market_events(
        classified
    )

    events = [
        build_market_event(event)
        for event in filtered
    ]

    print(
        f"Collected {len(events)} actionable event(s)."
    )

    return events

