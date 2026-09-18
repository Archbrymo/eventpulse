from types import SimpleNamespace
from app.risk import (
    MAX_TRADE_PORTFOLIO_PCT,
    approve_signal,
    calculate_quantity_from_notional,
    calculate_trade_notional,
    evaluate_market_gates,
    portfolio_risk_allowed,
)

def sig(direction="BUY", confidence=0.70, ticker="NVDA"):
    return SimpleNamespace(direction=direction, confidence=confidence, ticker=ticker)

def test_hold_and_wait_rejected():
    assert approve_signal(sig("HOLD", 0.99)) is False
    assert approve_signal(sig("WAIT", 0.99)) is False

def test_confidence_floor():
    assert approve_signal(sig("BUY", 0.59)) is False
    assert approve_signal(sig("BUY", 0.60)) is True

def test_daily_loss_boundary():
    ok, _ = portfolio_risk_allowed(98.01, 100, daily_start_equity=100)
    blocked, _ = portfolio_risk_allowed(98.00, 100, daily_start_equity=100)
    assert ok is True
    assert blocked is False

def test_drawdown_boundary():
    ok, _ = portfolio_risk_allowed(90.01, 100)
    blocked, _ = portfolio_risk_allowed(90.00, 100)
    assert ok is True
    assert blocked is False

def test_buy_notional_caps():
    value = calculate_trade_notional(sig("BUY", 1.0), price=10, cash=1_000_000, current_quantity=0, portfolio_value=100_000)
    assert value <= 100_000 * MAX_TRADE_PORTFOLIO_PCT
    value = calculate_trade_notional(sig("BUY", 1.0), price=10, cash=100, current_quantity=0, portfolio_value=100_000)
    assert value == 100
    value = calculate_trade_notional(sig("BUY", 1.0), price=10, cash=1_000_000, current_quantity=2000, portfolio_value=100_000)
    assert value == 0

def test_sell_fractions():
    assert calculate_trade_notional(sig("SELL", 0.90), 10, 0, 10, 1000) == 100
    assert calculate_trade_notional(sig("SELL", 0.80), 10, 0, 10, 1000) == 50
    assert calculate_trade_notional(sig("SELL", 0.70), 10, 0, 10, 1000) == 25

def test_quantity_zero_on_bad_price():
    assert calculate_quantity_from_notional(100, 0) == 0
    assert calculate_quantity_from_notional(100, 10) == 10

def test_market_gates():
    assert evaluate_market_gates(spread_bps=26)[0] is False
    assert evaluate_market_gates(turnover_24h=4_900_000)[0] is False
    assert evaluate_market_gates(trades_today=8)[0] is False
    assert evaluate_market_gates(spread_bps=25, turnover_24h=5_000_000, trades_today=7)[0] is True
