from __future__ import annotations

from .contracts import MarketEvent

MIN_RELEVANCE = 0.50
MAX_EVENT_AGE_SECONDS = 6 * 60 * 60


def is_tradable_event(event: MarketEvent, *, test_event: bool = False) -> bool:
    if event.relevance < MIN_RELEVANCE:
        return False
    if not test_event and event.age_seconds > MAX_EVENT_AGE_SECONDS:
        return False
    return True


def rank_events(events: list[MarketEvent]) -> list[MarketEvent]:
    def score(ev: MarketEvent):
        freshness = max(0.0, 1.0 - (max(ev.age_seconds, 0.0) / MAX_EVENT_AGE_SECONDS))
        return (ev.relevance * freshness * ev.novelty, ev.relevance, -ev.age_seconds)

    return sorted(events, key=score, reverse=True)
