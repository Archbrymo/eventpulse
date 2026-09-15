from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

import requests


BITGET_BASE = "https://api.bitget.com"
CACHE_FILE = Path(".bitget_universe_cache.json")
CACHE_TTL_SECONDS = 6 * 60 * 60

FALLBACK_ASSETS = [
    {
        "symbol": "rAAPLUSDT",
        "base": "rAAPL",
        "quote": "USDT",
        "underlying": "AAPL",
        "status": "fallback",
    },
    {
        "symbol": "rNVDAUSDT",
        "base": "rNVDA",
        "quote": "USDT",
        "underlying": "NVDA",
        "status": "fallback",
    },
    {
        "symbol": "rMSFTUSDT",
        "base": "rMSFT",
        "quote": "USDT",
        "underlying": "MSFT",
        "status": "fallback",
    },
    {
        "symbol": "rAMZNUSDT",
        "base": "rAMZN",
        "quote": "USDT",
        "underlying": "AMZN",
        "status": "fallback",
    },
    {
        "symbol": "rMETAUSDT",
        "base": "rMETA",
        "quote": "USDT",
        "underlying": "META",
        "status": "fallback",
    },
    {
        "symbol": "rTSLAUSDT",
        "base": "rTSLA",
        "quote": "USDT",
        "underlying": "TSLA",
        "status": "fallback",
    },
    {
        "symbol": "rSPYUSDT",
        "base": "rSPY",
        "quote": "USDT",
        "underlying": "SPY",
        "status": "fallback",
    },
    {
        "symbol": "rQQQUSDT",
        "base": "rQQQ",
        "quote": "USDT",
        "underlying": "QQQ",
        "status": "fallback",
    },
]


def _request(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.get(
        BITGET_BASE + path,
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    if str(data.get("code")) != "00000":
        raise RuntimeError(
            f"Bitget API error: {data.get('code')} {data.get('msg')}"
        )

    return data


def _normalise_instrument(item: Dict[str, Any]) -> Dict[str, Any]:
    symbol = str(item.get("symbol", ""))

    base = str(
        item.get("baseCoin")
        or item.get("base")
        or ""
    )

    quote = str(
        item.get("quoteCoin")
        or item.get("quote")
        or ""
    )

    # Bitget returns Reality symbols such as:
    # RPBRUSDT with baseCoin=rPBR.
    #
    # Prefer baseCoin because it preserves the rToken name.
    if base.lower().startswith("r"):
        underlying = base[1:]
    elif symbol.upper().startswith("R") and symbol.upper().endswith("USDT"):
        underlying = symbol[1:-4]
        base = "r" + underlying
    else:
        underlying = base

    return {
        "symbol": symbol,
        "base": base,
        "quote": quote,
        "underlying": underlying.upper(),
        "status": "live",
        "isReality": str(item.get("isReality", "")).lower(),
        "raw": item,
    }


def discover_rtokens(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Discover Bitget Reality assets.

    Priority:
      1. Live Bitget instruments
      2. Fresh cached Bitget universe
      3. 8-asset demo fallback
    """

    if not force_refresh and CACHE_FILE.exists():
        try:
            payload = json.loads(CACHE_FILE.read_text())
            timestamp = float(payload.get("timestamp", 0))
            assets = payload.get("assets", [])

            if (
                assets
                and time.time() - timestamp < CACHE_TTL_SECONDS
            ):
                return assets
        except Exception:
            pass

    try:
        data = _request(
            "/api/v3/market/instruments",
            {"category": "SPOT"},
        )

        instruments = data.get("data", [])

        reality = [
            _normalise_instrument(item)
            for item in instruments
            if str(item.get("isReality", "")).lower() == "yes"
        ]

        if not reality:
            raise RuntimeError(
                "Bitget returned zero Reality instruments"
            )

        reality.sort(
            key=lambda x: x["underlying"]
        )

        CACHE_FILE.write_text(
            json.dumps(
                {
                    "timestamp": time.time(),
                    "source": "bitget",
                    "count": len(reality),
                    "assets": reality,
                },
                indent=2,
            )
        )

        print(
            f"[Bitget Universe] LIVE Reality universe: "
            f"{len(reality)} assets"
        )

        return reality

    except Exception as exc:
        print(
            "[Bitget Universe] live discovery unavailable: "
            f"{type(exc).__name__}: {exc}"
        )

        # Try stale cache before demo fallback.
        if CACHE_FILE.exists():
            try:
                payload = json.loads(CACHE_FILE.read_text())
                assets = payload.get("assets", [])

                if assets:
                    print(
                        "[Bitget Universe] Using cached Reality universe: "
                        f"{len(assets)} assets"
                    )
                    return assets
            except Exception:
                pass

        print(
            "[Bitget Universe] Using 8-asset demo fallback."
        )

        return FALLBACK_ASSETS


def get_universe_symbols(
    force_refresh: bool = False,
) -> List[str]:
    return [
        asset["symbol"]
        for asset in discover_rtokens(
            force_refresh=force_refresh
        )
    ]


def underlying_ticker(symbol: str) -> str:
    """
    Convert:
        RPBRUSDT -> PBR
        rPBRUSDT -> PBR
        rAAPL -> AAPL
    """

    value = str(symbol).upper()

    if value.endswith("USDT"):
        value = value[:-4]

    if value.startswith("R"):
        value = value[1:]

    return value


def get_bitget_tickers() -> Dict[str, Dict[str, Any]]:
    """
    Retrieve all Bitget SPOT tickers and retain only
    Reality tokens discovered from the instrument endpoint.
    """

    assets = discover_rtokens()
    allowed = {
        asset["symbol"].upper()
        for asset in assets
    }

    data = _request(
        "/api/v3/market/tickers",
        {"category": "SPOT"},
    )

    result: Dict[str, Dict[str, Any]] = {}

    for item in data.get("data", []):
        symbol = str(item.get("symbol", ""))
        symbol_upper = symbol.upper()

        if symbol_upper not in allowed:
            continue

        try:
            result[symbol] = {
                "symbol": symbol,
                "underlying": underlying_ticker(symbol),
                "last": float(item.get("lastPrice") or 0),
                "open": float(item.get("openPrice24h") or 0),
                "high": float(item.get("highPrice24h") or 0),
                "low": float(item.get("lowPrice24h") or 0),
                "volume": float(item.get("volume24h") or 0),
                "quote_volume": float(
                    item.get("turnover24h") or 0
                ),
                "change_pct": float(
                    item.get("price24hPcnt") or 0
                ) * 100,
                "bid": float(item.get("bid1Price") or 0),
                "ask": float(item.get("ask1Price") or 0),
                "timestamp": item.get("ts"),
            }
        except (TypeError, ValueError):
            continue

    return result


def score_asset(
    asset: Dict[str, Any],
    ticker: Dict[str, Any] | None = None,
) -> float:
    """
    Deterministic pre-Qwen opportunity score.

    Designed to reduce the full Reality universe to a
    researchable shortlist without making an investment
    decision.

    Components:
      liquidity      0-3
      momentum       0-2
      volatility     0-2
      spread quality 0-1
      extreme move  -2
    """

    if not ticker:
        return 0.0

    score = 0.0

    turnover = float(
        ticker.get("quote_volume", 0) or 0
    )

    change = float(
        ticker.get("change_pct", 0) or 0
    )

    last = float(
        ticker.get("last", 0) or 0
    )

    bid = float(
        ticker.get("bid", 0) or 0
    )

    ask = float(
        ticker.get("ask", 0) or 0
    )

    # -------------------------------------------------
    # 1. Liquidity: 0-3
    # -------------------------------------------------

    if turnover >= 500_000_000:
        score += 3.0
    elif turnover >= 100_000_000:
        score += 2.5
    elif turnover >= 25_000_000:
        score += 2.0
    elif turnover >= 5_000_000:
        score += 1.0

    # -------------------------------------------------
    # 2. Momentum: 0-2
    # -------------------------------------------------

    abs_change = abs(change)

    if abs_change >= 8:
        score += 2.0
    elif abs_change >= 4:
        score += 1.5
    elif abs_change >= 2:
        score += 1.0
    elif abs_change >= 1:
        score += 0.5

    # -------------------------------------------------
    # 3. Volatility / opportunity: 0-2
    # -------------------------------------------------

    if 2 <= abs_change <= 8:
        score += 2.0
    elif 1 <= abs_change < 2:
        score += 1.0
    elif 8 < abs_change <= 12:
        score += 1.0

    # -------------------------------------------------
    # 4. Spread quality: 0-1
    # -------------------------------------------------

    if last > 0 and bid > 0 and ask > 0:
        spread_pct = (
            (ask - bid) / last
        ) * 100

        if spread_pct <= 0.10:
            score += 1.0
        elif spread_pct <= 0.25:
            score += 0.5

    # -------------------------------------------------
    # 5. Extreme-move penalty
    # -------------------------------------------------

    if abs_change > 15:
        score -= 2.0
    elif abs_change > 12:
        score -= 1.0

    return round(score, 4)

def rank_candidates(
    limit: int = 50,
) -> List[Dict[str, Any]]:
    assets = discover_rtokens()
    tickers = get_bitget_tickers()

    ranked = []

    for asset in assets:
        symbol = asset["symbol"]

        ticker = tickers.get(symbol)

        score = score_asset(
            asset,
            ticker,
        )

        row = dict(asset)
        row["score"] = score
        row["ticker_data"] = ticker

        ranked.append(row)

    ranked.sort(
        key=lambda x: (
            x["score"],
            (
                x.get("ticker_data") or {}
            ).get("quote_volume", 0),
        ),
        reverse=True,
    )

    return ranked[:limit]


def universe_summary() -> Dict[str, Any]:
    assets = discover_rtokens()
    tickers = get_bitget_tickers()

    live = sum(
        1
        for x in assets
        if x.get("status") == "live"
    )

    return {
        "total": len(assets),
        "live": live,
        "tickers": len(tickers),
        "source": (
            "Bitget Reality"
            if live
            else "Fallback"
        ),
        "status": (
            "LIVE"
            if live
            else "FALLBACK"
        ),
    }
