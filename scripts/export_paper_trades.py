import csv
import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "eventpulse.db"
OUT = Path(__file__).resolve().parents[1] / "paper_trading_log.csv"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

trades = conn.execute(
    "SELECT * FROM trades ORDER BY id ASC"
).fetchall()

output = []

for trade in trades:
    r = dict(trade)

    timestamp = r.get("timestamp") or ""
    ticker = r.get("ticker") or r.get("execution_symbol") or ""
    direction = r.get("side") or ""
    price = float(r.get("price") or 0)
    quantity = float(r.get("quantity") or 0)
    notional = float(r.get("value") or price * quantity)

    # Reconstruct cash movement from the trade.
    # BUY decreases cash; SELL increases cash.
    if direction.upper() == "BUY":
        balance_change = -notional
    elif direction.upper() == "SELL":
        balance_change = notional
    else:
        balance_change = 0.0

    output.append({
        "timestamp": timestamp,
        "instrument": ticker,
        "direction": direction,
        "price": price,
        "quantity": quantity,
        "notional": round(notional, 6),
        "balance_change": round(balance_change, 6),
        "trade_id": r.get("id", ""),
        "confidence": r.get("confidence", ""),
        "execution_symbol": r.get("execution_symbol", ""),
        "reasoning": r.get("reasoning", ""),
        "raw_trade": json.dumps(r, default=str),
    })

fieldnames = [
    "timestamp",
    "instrument",
    "direction",
    "price",
    "quantity",
    "notional",
    "balance_change",
    "trade_id",
    "confidence",
    "execution_symbol",
    "reasoning",
    "raw_trade",
]

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output)

conn.close()

print(f"Trades exported: {len(output)}")
print(f"CSV: {OUT}")

if output:
    print("\nLatest paper trade:")
    latest = output[-1]
    for key in fieldnames[:-1]:
        print(f"{key}: {latest[key]}")
else:
    print("WARNING: No paper trades recorded.")
