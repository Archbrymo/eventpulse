
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "eventpulse.db"



def save_agent_cycle(
    cycle_id,
    stage,
    status,
    detail="",
    ticker="",
    decision="",
    confidence=None,
):
    """Persist an observable event-driven agent cycle stage."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                ticker TEXT,
                decision TEXT,
                confidence REAL,
                detail TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO agent_cycles
            (cycle_id, timestamp, stage, status, ticker, decision,
             confidence, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(cycle_id),
                datetime.utcnow().isoformat(),
                str(stage),
                str(status),
                str(ticker or ""),
                str(decision or ""),
                confidence,
                str(detail or ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_agent_cycle(cycle_id=None, limit=100):
    """Return observable agent-cycle audit rows."""
    conn = get_connection()
    try:
        if cycle_id:
            rows = conn.execute(
                """
                SELECT id, cycle_id, timestamp, stage, status,
                       ticker, decision, confidence, detail
                FROM agent_cycles
                WHERE cycle_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (str(cycle_id), int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, cycle_id, timestamp, stage, status,
                       ticker, decision, confidence, detail
                FROM agent_cycles
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return rows
    finally:
        conn.close()

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
            equity REAL NOT NULL,
            positions TEXT,
            updated_at TEXT
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




# ============================================================
# EVENTPULSE DATABASE MIGRATIONS
# ============================================================

EVENTPULSE_SCHEMA_VERSION = 3


def _table_columns(conn, table):
    rows = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()
    return {row[1] for row in rows}


def _ensure_schema_meta(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)


def _schema_version(conn):
    _ensure_schema_meta(conn)
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
    ).fetchone()
    try:
        return int(row[0]) if row else 0
    except Exception:
        return 0


def _set_schema_version(conn, version):
    conn.execute("""
        INSERT INTO schema_meta(key, value)
        VALUES ('schema_version', ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, (str(version),))


def run_migrations(conn):
    """
    Forward-only SQLite migrations.

    Migrations are additive and idempotent. Existing trading data
    is preserved wherever possible.
    """
    _ensure_schema_meta(conn)
    version = _schema_version(conn)

    # --------------------------------------------------------
    # V1: canonical portfolio schema
    # --------------------------------------------------------
    if version < 1:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cash REAL NOT NULL DEFAULT 0,
                equity REAL NOT NULL DEFAULT 0,
                positions_json TEXT NOT NULL DEFAULT '{}'
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS initial_positions (
                ticker TEXT PRIMARY KEY,
                quantity REAL NOT NULL DEFAULT 0,
                average_price REAL NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT,
                side TEXT,
                quantity REAL,
                price REAL,
                notional REAL,
                status TEXT,
                research_ticker TEXT,
                execution_symbol TEXT
            )
        """)

        _set_schema_version(conn, 1)
        version = 1

    # --------------------------------------------------------
    # V2: compatibility columns for legacy trade schemas
    # --------------------------------------------------------
    if version < 2:
        columns = _table_columns(conn, "trades")

        additions = {
            "research_ticker": "TEXT",
            "execution_symbol": "TEXT",
            "status": "TEXT",
            "notional": "REAL",
        }

        for column, definition in additions.items():
            if column not in columns:
                conn.execute(
                    f'ALTER TABLE trades ADD COLUMN "{column}" {definition}'
                )

        _set_schema_version(conn, 2)
        version = 2

    # --------------------------------------------------------
    # V3: portfolio valuation snapshots
    # --------------------------------------------------------
    if version < 3:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cash REAL NOT NULL DEFAULT 0,
                position_value REAL NOT NULL DEFAULT 0,
                equity REAL NOT NULL DEFAULT 0
            )
        """)

        _set_schema_version(conn, 3)
        version = 3

    conn.commit()
    return version


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


def save_qwen_decision(
    ticker,
    decision,
    confidence=None,
    price=None,
    reasoning="",
    catalyst="",
    fundamental_thesis="",
    valuation_thesis="",
    market_thesis="",
    bull_case="",
    bear_case="",
    invalidation_condition="",
    expected_horizon="",
):
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS qwen_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT NOT NULL,
                decision TEXT NOT NULL,
                confidence REAL,
                price REAL,
                reasoning TEXT,
                catalyst TEXT,
                fundamental_thesis TEXT,
                valuation_thesis TEXT,
                market_thesis TEXT,
                bull_case TEXT,
                bear_case TEXT,
                invalidation_condition TEXT,
                expected_horizon TEXT
            )
            """
        )

        conn.execute(
            """
            INSERT INTO qwen_decisions (
                timestamp,
                ticker,
                decision,
                confidence,
                price,
                reasoning,
                catalyst,
                fundamental_thesis,
                valuation_thesis,
                market_thesis,
                bull_case,
                bear_case,
                invalidation_condition,
                expected_horizon
            )
            VALUES (
                datetime('now'),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                str(ticker),
                str(decision).upper(),
                float(confidence) if confidence is not None else None,
                float(price) if price is not None else None,
                reasoning or "",
                catalyst or "",
                fundamental_thesis or "",
                valuation_thesis or "",
                market_thesis or "",
                bull_case or "",
                bear_case or "",
                invalidation_condition or "",
                expected_horizon or "",
            ),
        )

        conn.commit()
    finally:
        conn.close()


def get_qwen_decision_history(limit=100, ticker=None):
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS qwen_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT NOT NULL,
                decision TEXT NOT NULL,
                confidence REAL,
                price REAL,
                reasoning TEXT,
                catalyst TEXT,
                fundamental_thesis TEXT,
                valuation_thesis TEXT,
                market_thesis TEXT,
                bull_case TEXT,
                bear_case TEXT,
                invalidation_condition TEXT,
                expected_horizon TEXT
            )
            """
        )

        if ticker:
            cur = conn.execute(
                """
                SELECT *
                FROM qwen_decisions
                WHERE ticker = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(ticker).upper(), int(limit)),
            )
        else:
            cur = conn.execute(
                """
                SELECT *
                FROM qwen_decisions
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            )

        return cur.fetchall()
    finally:
        conn.close()


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
    equity_value = float(equity if equity is not None else cash)
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO portfolio (
            timestamp,
            cash,
            equity,
            positions,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        now,
        cash,
        equity_value,
        positions_json,
        now,
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
            equity,
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
        "cash": float(row[0] or 0.0),
        "equity": float(row[1] or row[0] or 0.0),
        "positions": json.loads(row[2]) if row[2] else {},
        "updated_at": row[3],
    }

def load_portfolio():
    portfolio = get_latest_portfolio()

    if portfolio is None:
        portfolio = {
            "cash": 100000.0,
            "equity": 100000.0,
            "positions": {},
        }

        save_portfolio(portfolio, equity=100000.0)

    return (
        float(portfolio.get("cash", 100000.0)),
        portfolio.get("positions", {}),
    )

