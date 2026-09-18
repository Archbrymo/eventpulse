import json
import sqlite3
from pathlib import Path

import pytest


def test_risk_module_imports():
    from app.risk import approve_signal, calculate_position_size
    assert callable(approve_signal)
    assert callable(calculate_position_size)


def test_execution_module_imports():
    from app.execution import PaperExecutor
    assert PaperExecutor is not None


def test_portfolio_normalization():
    from app.portfolio_service import normalize_portfolio

    portfolio = normalize_portfolio({
        "cash": "1000",
        "positions": {
            "rNVDA": {
                "quantity": "2",
                "average_price": "100",
            }
        },
    })

    assert portfolio["cash"] == 1000.0
    assert portfolio["positions"]["rNVDA"]["quantity"] == 2.0
    assert portfolio["positions"]["rNVDA"]["average_price"] == 100.0


def test_dynamic_mark_to_market():
    from app.portfolio_service import mark_to_market

    result = mark_to_market(
        {
            "cash": 1000,
            "positions": {
                "rNVDA": {
                    "quantity": 2,
                    "average_price": 100,
                }
            },
        },
        {
            "rNVDA": 125,
        },
    )

    assert result["position_value"] == 250
    assert result["equity"] == 1250


def test_database_migrations():
    from app.database import get_connection

    conn = get_connection()

    try:
        row = conn.execute(
            "SELECT value FROM schema_meta "
            "WHERE key = 'schema_version'"
        ).fetchone()

        assert row is not None
        assert int(row[0]) >= 3

        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            ).fetchall()
        }

        assert "portfolios" in tables
        assert "initial_positions" in tables
        assert "trades" in tables
        assert "equity_snapshots" in tables
    finally:
        conn.close()
