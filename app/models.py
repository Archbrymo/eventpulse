from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    WAIT = "WAIT"


class AssetSignal(BaseModel):
    ticker: str

    direction: Direction

    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    reasoning: str

    catalyst: Optional[str] = None

    fundamental_thesis: Optional[str] = None

    valuation_thesis: Optional[str] = None

    market_thesis: Optional[str] = None

    bull_case: Optional[str] = None

    bear_case: Optional[str] = None

    invalidation_condition: Optional[str] = None

    expected_horizon: Optional[str] = None

    position_reasoning: Optional[str] = None


class TradingDecision(BaseModel):
    event: str

    market_regime: str

    summary: str

    signals: list[AssetSignal]
