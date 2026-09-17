from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(".eventpulse_eventlog.jsonl")
PIPELINE_PATH = Path(".eventpulse_pipeline.json")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_cycle_id() -> str:
    return utcnow().strftime("%Y%m%dT%H%M%SZ")


def append_cycle_event(
    cycle_id: str,
    stage: str,
    status: str,
    message: str = "",
    ticker: str = "",
    event_id: str = "",
    payload: dict | None = None,
) -> None:
    row = {
        "ts": utcnow().isoformat(),
        "cycle_id": cycle_id,
        "stage": stage,
        "status": status,
        "event_id": event_id,
        "ticker": ticker,
        "message": message,
        "payload": payload or {},
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def load_pipeline() -> dict:
    if not PIPELINE_PATH.exists():
        return {}
    try:
        return json.loads(PIPELINE_PATH.read_text())
    except Exception:
        return {}


def finalist_quality(ticker: str) -> dict:
    snap = load_pipeline()
    needle = str(ticker or "").upper()
    for row in snap.get("finalists") or []:
        if str(row.get("ticker") or "").upper() == needle:
            return row
    return {}


def paper_loop(seconds: int | None = None) -> None:
    from main import main

    delay = int(seconds or os.environ.get("EVENTPULSE_LOOP_SECONDS", "60"))
    while True:
        main()
        print(f"sleeping {delay}s before next cycle")
        time.sleep(delay)
