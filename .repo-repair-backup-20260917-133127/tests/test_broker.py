from app.broker import PaperBroker
from app.execution import PaperExecutor

def book(cash=1000):
    return {"cash": cash, "positions": {}}

def test_buy_vwap_and_cash():
    p = book(1000)
    b = PaperBroker(p)
    assert b.buy("rNVDA", 10, quantity=10)["success"]
    assert p["cash"] == 900
    assert b.buy("rNVDA", 20, quantity=10)["success"]
    assert p["positions"]["rNVDA"]["quantity"] == 20
    assert p["positions"]["rNVDA"]["average_price"] == 15

def test_buy_insufficient_cash():
    p = book(50)
    assert PaperBroker(p).buy("rNVDA", 10, quantity=10)["success"] is False

def test_sell_rules():
    p = {"cash": 0, "positions": {"rNVDA": {"quantity": 10, "average_price": 10}}}
    b = PaperBroker(p)
    assert b.sell("rAAPL", 10, quantity=1)["success"] is False
    assert b.sell("rNVDA", 12, quantity=10)["success"]
    assert "rNVDA" not in p["positions"]
    assert p["cash"] == 120

def test_executor_maps_research_ticker():
    p = book(10_000)
    result = PaperExecutor(p).execute("NVDA", "BUY", price=100, quantity=1)
    assert result["success"]
    assert result["execution_symbol"] == "rNVDA"
    assert "rNVDA" in p["positions"]

def test_unsupported_side():
    result = PaperExecutor(book()).execute("NVDA", "HOLD", price=100, quantity=1)
    assert result["success"] is False
