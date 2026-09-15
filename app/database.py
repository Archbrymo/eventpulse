
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "eventpulse.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            execution_symbol TEXT,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            notional REAL NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'FILLED'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cash REAL NOT NULL,
            equity REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS initial_positions (
            execution_symbol TEXT PRIMARY KEY,
            quantity REAL NOT NULL,
            average_price REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            source TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equity_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            equity REAL NOT NULL,
            cash REAL NOT NULL,
            daily_start_equity REAL,
            drawdown_pct REAL,
            daily_pnl_pct REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS theses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL,
            confidence REAL NOT NULL,
            thesis TEXT NOT NULL,
            catalyst TEXT,
            bull_case TEXT,
            bear_case TEXT,
            invalidation_condition TEXT,
            expected_horizon TEXT,
            entry_price REAL NOT NULL,
            current_price REAL,
            return_pct REAL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            resolved_at TEXT,
            resolution_reason TEXT,
            event_key TEXT
        )
    """)

    # Migrate older databases that may not have event_key.
    cursor.execute("""
        PRAGMA table_info(theses)
    """)

    thesis_columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "event_key" not in thesis_columns:
        cursor.execute("""
            ALTER TABLE theses
            ADD COLUMN event_key TEXT
        """)

    conn.commit()
    conn.close()


def initialize_database():
    """
    Backward-compatible wrapper used by older code.
    """
    init_db()


def save_trade(
    ticker,
    side,
    quantity,
    price,
    reason="",
    execution_symbol=None,
    status="FILLED",
    confidence=None,
    reasoning=None,
):
    conn = get_connection()
    cursor = conn.cursor()

    ticker = str(ticker)
    side = str(side)
    quantity = float(quantity)
    price = float(price)

    execution_symbol = (
        str(execution_symbol)
        if execution_symbol is not None
        else None
    )

    value = quantity * price

    if reasoning is None:
        reasoning = reason

    cursor.execute("""
        INSERT INTO trades (
            timestamp,
            ticker,
            execution_symbol,
            side,
            quantity,
            price,
            value,
            confidence,
            reasoning
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        ticker,
        execution_symbol,
        side,
        quantity,
        price,
        value,
        float(confidence) if confidence is not None else None,
        str(reasoning or ""),
    ))

    trade_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return trade_id

def log_trade(
    ticker,
    side,
    quantity,
    price,
    notional=None,
    reason="",
    execution_symbol=None,
    status="FILLED",
):
    return save_trade(
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        reason=reason,
        execution_symbol=execution_symbol,
        status=status,
    )

def get_trades():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            timestamp,
            ticker,
            side,
            quantity,
            price,
            value,
            confidence,
            reasoning
        FROM trades
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows



def has_recent_buy(ticker, cooldown_minutes=60):
    """Return True if ticker had a recent filled BUY."""
    from datetime import datetime, timedelta

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT timestamp
        FROM trades
        WHERE ticker = ?
          AND side = 'BUY'
        ORDER BY id DESC
        LIMIT 1
        """,
        (str(ticker),),
    )

    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        return False

    try:
        trade_time = datetime.fromisoformat(
            str(row[0]).replace("Z", "+00:00")
        )

        now = datetime.now(trade_time.tzinfo)

        return now - trade_time < timedelta(
            minutes=cooldown_minutes
        )

    except (ValueError, TypeError):
        return False


def save_portfolio(
    portfolio,
    equity=None,
):
    import json

    cash = float(portfolio.get("cash", 0.0))
    positions = portfolio.get("positions", {})
    positions_json = json.dumps(positions, default=float)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO portfolio (
            cash,
            positions,
            updated_at
        )
        VALUES (?, ?, ?)
    """, (
        cash,
        positions_json,
        datetime.utcnow().isoformat(),
    ))

    conn.commit()
    conn.close()

def get_latest_portfolio():
    import json

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            cash,
            positions,
            updated_at
        FROM portfolio
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "cash": float(row[0]),
        "positions": json.loads(row[1] or "{}"),
        "updated_at": row[2],
    }


def save_initial_position(
    execution_symbol,
    quantity,
    average_price,
):
    conn = get_connection()
    cursor = conn.cursor()

    execution_symbol = str(execution_symbol)
    quantity = float(quantity)
    average_price = float(average_price)

    cursor.execute("""
        INSERT INTO initial_positions (
            execution_symbol,
            quantity,
            average_price
        )
        VALUES (?, ?, ?)
        ON CONFLICT(execution_symbol)
        DO UPDATE SET
            quantity = excluded.quantity,
            average_price = excluded.average_price
    """, (
        execution_symbol,
        quantity,
        average_price,
    ))

    conn.commit()
    conn.close()


def get_initial_positions():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            symbol,
            quantity,
            average_price
        FROM initial_positions
        ORDER BY symbol
    """)

    rows = cursor.fetchall()

    conn.close()

    return {
        str(row[0]): {
            "quantity": float(row[1]),
            "average_price": float(row[2]),
        }
        for row in rows
    }

def save_meta(
    key,
    value,
):
    conn = get_connection()
    cursor = conn.cursor()

    key = str(key)
    value = str(value)

    cursor.execute("""
        INSERT INTO portfolio_meta (
            key,
            value
        )
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET
            value = excluded.value
    """, (
        key,
        value,
    ))

    conn.commit()
    conn.close()


def get_meta(
    key,
    default=None,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT value
        FROM portfolio_meta
        WHERE key = ?
    """, (
        str(key),
    ))

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return default

    return row[0]


def set_daily_start_date(
    date_string,
):
    save_meta(
        "daily_start_date",
        date_string,
    )


def get_daily_start_date():
    return get_meta(
        "daily_start_date"
    )


def set_daily_start_equity(
    equity,
):
    save_meta(
        "daily_start_equity",
        float(equity),
    )


def get_daily_start_equity():
    value = get_meta(
        "daily_start_equity"
    )

    if value is None:
        return None

    return float(value)


def set_initial_cash(
    cash,
):
    save_meta(
        "initial_cash",
        float(cash),
    )


def get_initial_cash():
    value = get_meta(
        "initial_cash"
    )

    if value is None:
        return None

    return float(value)


def get_initial_equity():
    initial_cash = get_initial_cash()

    if initial_cash is None:
        initial_cash = 0.0

    positions = get_initial_positions()

    position_value = 0.0

    for position in positions.values():
        quantity = float(
            position.get(
                "quantity",
                0.0,
            )
        )

        average_price = float(
            position.get(
                "average_price",
                0.0,
            )
        )

        position_value += (
            quantity * average_price
        )

    return (
        float(initial_cash)
        + position_value
    )


def load_initial_portfolio():
    cash = get_initial_cash()

    if cash is None:
        cash = 0.0

    positions = get_initial_positions()

    return {
        "cash": float(cash),
        "positions": positions,
    }


def log_event(
    title,
    summary,
    source,
):
    conn = get_connection()
    cursor = conn.cursor()

    title = str(title)
    summary = str(summary or "")
    source = str(source or "")

    cursor.execute("""
        INSERT INTO events (
            timestamp,
            title,
            summary,
            source
        )
        VALUES (?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        title,
        summary,
        source,
    ))

    event_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return int(event_id)


def get_events(
    limit=100,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            timestamp,
            title,
            summary,
            source
        FROM events
        ORDER BY id DESC
        LIMIT ?
    """, (
        int(limit),
    ))

    rows = cursor.fetchall()

    conn.close()

    return rows


def save_equity_snapshot(
    equity,
    cash=None,
    daily_start_equity=None,
    drawdown_pct=None,
    daily_pnl_pct=None,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO equity_snapshots (
            timestamp,
            equity
        )
        VALUES (?, ?)
    """, (
        datetime.utcnow().isoformat(),
        float(equity),
    ))

    snapshot_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return snapshot_id

def log_equity_snapshot(
    equity,
    cash,
    daily_start_equity=None,
    drawdown_pct=None,
    daily_pnl_pct=None,
):
    return save_equity_snapshot(
        equity=equity,
        cash=cash,
        daily_start_equity=daily_start_equity,
        drawdown_pct=drawdown_pct,
        daily_pnl_pct=daily_pnl_pct,
    )

def create_thesis(
    ticker,
    direction,
    confidence,
    thesis,
    catalyst=None,
    bull_case=None,
    bear_case=None,
    invalidation_condition=None,
    expected_horizon=None,
    entry_price=None,
    event_key=None,
):
    conn = get_connection()
    cursor = conn.cursor()

    if event_key:
        cursor.execute(
            """
            SELECT id
            FROM theses
            WHERE event_key = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (str(event_key),),
        )
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return existing[0]

    cursor.execute(
        """
        INSERT INTO theses (
            created_at,
            ticker,
            direction,
            confidence,
            thesis,
            catalyst,
            bull_case,
            bear_case,
            invalidation_condition,
            expected_horizon,
            entry_price,
            current_price,
            return_pct,
            status,
            event_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            str(ticker),
            str(direction),
            float(confidence),
            str(thesis or ""),
            catalyst,
            bull_case,
            bear_case,
            invalidation_condition,
            expected_horizon,
            float(entry_price) if entry_price is not None else None,
            float(entry_price) if entry_price is not None else None,
            0.0,
            "OPEN",
            str(event_key) if event_key else None,
        ),
    )

    thesis_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return thesis_id


def get_open_theses():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            created_at,
            ticker,
            direction,
            confidence,
            thesis,
            catalyst,
            bull_case,
            bear_case,
            invalidation_condition,
            expected_horizon,
            entry_price,
            current_price,
            return_pct,
            status,
            resolved_at,
            resolution_reason
        FROM theses
        WHERE status = 'OPEN'
        ORDER BY id ASC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def update_thesis(
    thesis_id,
    current_price=None,
    return_pct=None,
    status=None,
    resolution_reason=None,
):
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    values = []

    if current_price is not None:
        updates.append("current_price = ?")
        values.append(float(current_price))

    if return_pct is not None:
        updates.append("return_pct = ?")
        values.append(float(return_pct))

    if status is not None:
        updates.append("status = ?")
        values.append(str(status))

        if str(status) in ("VALIDATED", "INVALIDATED"):
            updates.append("resolved_at = ?")
            values.append(datetime.utcnow().isoformat())

    if resolution_reason is not None:
        updates.append("resolution_reason = ?")
        values.append(str(resolution_reason))

    if not updates:
        conn.close()
        return

    values.append(int(thesis_id))

    cursor.execute(
        f"""
        UPDATE theses
        SET {", ".join(updates)}
        WHERE id = ?
        """,
        values,
    )

    conn.commit()
    conn.close()


def get_equity_history():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            timestamp,
            NULL AS cash,
            equity
        FROM equity_snapshots
        ORDER BY id ASC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def load_portfolio():
    portfolio = get_latest_portfolio()

    if portfolio is None:
        return 0.0, {}

    return (
        float(portfolio.get("cash", 0.0)),
        portfolio.get("positions", {}),
    )
