from app.assets import get_execution_symbol, get_underlying

def test_nvda_maps_to_rtoken():
    assert get_execution_symbol("NVDA") == "rNVDA"

def test_underlying_strips_prefix_and_quote():
    assert get_underlying("rNVDAUSDT") == "NVDA"

def test_unknown_ticker_gets_prefix():
    assert get_execution_symbol("AMD") == "rAMD"
