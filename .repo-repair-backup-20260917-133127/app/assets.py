from typing import Dict, List, Tuple

from .bitget_universe import (
    discover_rtokens,
    get_universe_symbols,
    underlying_ticker,
)

# Stable fallback/demo universe.
ASSET_MAP = {
    "SPY": "rSPY",
    "QQQ": "rQQQ",
    "NVDA": "rNVDA",
    "AAPL": "rAAPL",
    "MSFT": "rMSFT",
    "AMZN": "rAMZN",
    "META": "rMETA",
    "TSLA": "rTSLA",
}


def get_execution_symbol(ticker: str) -> str:
    ticker = ticker.upper()

    if ticker.startswith("R"):
        return ticker

    return ASSET_MAP.get(ticker, f"r{ticker}")


def get_underlying(execution_symbol: str) -> str:
    value = execution_symbol.upper()

    if value.startswith("R"):
        value = value[1:]

    if value.endswith("USDT"):
        value = value[:-4]

    return value


def supported_assets() -> List[str]:
    return list(ASSET_MAP.keys())


def dynamic_supported_assets() -> List[str]:
    """
    Return all currently discovered Reality assets as underlying tickers.
    """
    return [
        underlying_ticker(symbol)
        for symbol in get_universe_symbols()
    ]


def dynamic_asset_map() -> Dict[str, str]:
    """
    Build underlying ticker -> Bitget Reality symbol dynamically.
    """
    result = {}

    for asset in discover_rtokens():
        symbol = asset["symbol"]
        result[underlying_ticker(symbol)] = symbol.replace("USDT", "")

    # Preserve known mappings even if discovery is temporarily unavailable.
    result.update(ASSET_MAP)

    return result
