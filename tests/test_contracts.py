from datetime import datetime, timezone, timedelta
from app.contracts import MarketEvent, make_event_id, make_event_key

def test_event_id_stable():
    ts = datetime(2026, 9, 17, tzinfo=timezone.utc)
    a = make_event_id("yahoo", ts, "NVDA beats earnings")
    b = make_event_id("yahoo", ts, "nvda   beats earnings")
    assert a == b

def test_event_key_clusters_headline():
    assert make_event_key("nvda", "NVDA Beats Earnings") == make_event_key("NVDA", "nvda beats earnings")

def test_legacy_event_and_age():
    detected = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
    published = detected - timedelta(hours=7)
    event = MarketEvent.from_legacy(
        {
            "ticker": "NVDA",
            "headline": "NVDA beats earnings",
            "relevance": 0.8,
            "catalyst": "positive",
            "reason": "earnings beat",
            "published_at": published.isoformat(),
        },
        detected_at=detected,
    )
    assert event.tickers == ["NVDA"]
    assert event.age_seconds == 7 * 3600
    assert event.relevance >= 0.50
