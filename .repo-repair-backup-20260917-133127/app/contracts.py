from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from hashlib import sha1
from typing import Any, Optional

from pydantic import BaseModel, Field

from .models import AssetSignal, Direction, TradingDecision


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_headline(headline: str) -> str:
    return " ".join(str(headline).lower().split())


def make_event_id(source: str, published_at: datetime, headline: str) -> str:
    raw = f"{source}|{published_at.isoformat()}|{normalize_headline(headline)}"
    return sha1(raw.encode("utf-8")).hexdigest()


def make_event_key(ticker: str, headline: str) -> str:
    return f"{str(ticker).upper()}|{normalize_headline(headline)}"


class EventType(str, Enum):
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    MNA = "mna"
    REGULATION = "regulation"
    LISTING = "listing"
    MACRO = "macro"
    PRODUCT = "product"
    ANALYST = "analyst"
    OTHER = "other"


class EventSentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class MarketEvent(BaseModel):
    event_id: str
    event_key: str
    source: str
    source_url: Optional[str] = None
    published_at: datetime
    detected_at: datetime
    headline: str
    summary: str = ""
    event_type: EventType = EventType.OTHER
    sentiment: EventSentiment = EventSentiment.NEUTRAL
    relevance: float = Field(ge=0, le=1)
    novelty: float = Field(ge=0, le=1, default=1.0)
    tickers: list[str]
    execution_symbols: list[str] = Field(default_factory=list)
    reason: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        return (self.detected_at - self.published_at).total_seconds()

    @classmethod
    def from_legacy(cls, event: dict, detected_at: Optional[datetime] = None) -> "MarketEvent":
        detected = detected_at or utcnow()
        published = event.get("published_at") or event.get("pubDate") or detected
        if isinstance(published, str):
            published = datetime.fromisoformat(published.replace("Z", "+00:00"))
        ticker = str(event.get("ticker") or "").upper()
        headline = str(event.get("headline") or event.get("title") or "")
        tickers = event.get("tickers") or ([ticker] if ticker else [])
        source = str(event.get("source") or "yahoo")
        catalyst = str(event.get("catalyst") or "neutral").lower()
        sentiment = EventSentiment(catalyst) if catalyst in EventSentiment._value2member_map_ else EventSentiment.NEUTRAL
        return cls(
            event_id=make_event_id(source, published, headline),
            event_key=make_event_key(ticker or (tickers[0] if tickers else "UNK"), headline),
            source=source,
            published_at=published,
            detected_at=detected,
            headline=headline,
            summary=str(event.get("summary") or event.get("reason") or ""),
            sentiment=sentiment,
            relevance=float(event.get("relevance") or 0.0),
            tickers=[str(t).upper() for t in tickers],
            reason=str(event.get("reason") or ""),
            raw=event,
        )


class Instrument(BaseModel):
    underlying: str
    execution_symbol: str
    last: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread_bps: Optional[float] = None
    change_pct_24h: float = 0.0
    turnover_24h: float = 0.0
    fast_score: float = 0.0
    evidence_score: float = 0.0
    evidence_breakdown: dict[str, float] = Field(default_factory=dict)
    event_match: bool = False


class EvidenceBlock(BaseModel):
    source: str
    as_of: datetime
    stale: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)
    text: str = ""


class ResearchPack(BaseModel):
    event: MarketEvent
    instrument: Instrument
    blocks: list[EvidenceBlock] = Field(default_factory=list)
    portfolio_snapshot: dict[str, Any] = Field(default_factory=dict)


class AgentName(str, Enum):
    EVENT = "event"
    MICROSTRUCTURE = "microstructure"
    FUNDAMENTAL = "fundamental"
    PORTFOLIO = "portfolio"
    DEVIL = "devil"


class AgentVote(BaseModel):
    agent: AgentName
    ticker: str
    direction: Direction
    confidence: float = Field(ge=0, le=1)
    veto: bool = False
    veto_reason: Optional[str] = None
    notes: str = ""
    used_block_sources: list[str] = Field(default_factory=list)


class CouncilDecision(TradingDecision):
    cycle_id: str = ""
    event_id: str = ""
    votes: list[AgentVote] = Field(default_factory=list)
    dissent: bool = False
    wait_reason: Optional[str] = None


class RiskVerdict(BaseModel):
    approved: bool
    reason: str
    ticker: str
    side: Direction
    requested_notional: float = 0.0
    approved_notional: float = 0.0
    quantity: float = 0.0
    max_position_pct: float = 0.20
    stop_price: Optional[float] = None
    time_stop_at: Optional[datetime] = None
    sizing: str = "percent"


class FillResult(BaseModel):
    success: bool
    research_ticker: str
    execution_symbol: str
    side: str
    price: float = 0.0
    quantity: float = 0.0
    notional: float = 0.0
    fee: float = 0.0
    slippage_bps: float = 0.0
    reason: Optional[str] = None
