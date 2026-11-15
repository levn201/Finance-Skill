import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import depot_core as dc  # noqa: E402


def depot_with(*steps):
    depot = dc.empty_depot()
    notes = []
    for fn, *args in steps:
        depot, n = fn(depot, *args)
        notes += n
    return depot, notes


# --- changes -----------------------------------------------------------------------------------


def test_add_position_with_optional_fields():
    depot, _ = depot_with((dc.add_position, "sap.de", 10, 180, None, "SAP SE"), (dc.add_position, "AAPL"))
    sap, aapl = depot["positions"]
    assert sap["symbol"] == "SAP.DE" and sap["quantity"] == 10 and sap["entry_price"] == 180
    assert sap["entry_currency"] == "EUR"  # defaults to the base currency
    assert aapl["quantity"] is None and aapl["entry_price"] is None


def test_add_does_not_mutate_input_and_rejects_duplicates():
    original = dc.empty_depot()
    depot, _ = dc.add_position(original, "SAP.DE", 1)
    assert original["positions"] == []
    with pytest.raises(dc.DepotError, match="already in the Depot"):
        dc.add_position(depot, "sap.de", 1)


@pytest.mark.parametrize("kwargs, message", [
    ({"symbol": "SAP SE"}, "not a valid symbol"),
    ({"symbol": "SAP.DE", "quantity": 0}, "greater than 0"),
    ({"symbol": "SAP.DE", "quantity": -3}, "greater than 0"),
    ({"symbol": "SAP.DE", "entry_price": "abc"}, "must be a number"),
    ({"symbol": "SAP.DE", "entry_currency": "EURO"}, "currency code"),
    ({"symbol": "SAP.DE", "isin": "DE123"}, "valid ISIN"),
])
def test_add_rejects_invalid_input(kwargs, message):
    with pytest.raises(dc.DepotError, match=message):
        dc.add_position(dc.empty_depot(), **kwargs)


def test_buying_moves_instrument_off_the_watchlist():
    depot, notes = depot_with((dc.watch, "ASML.AS", "ASML"), (dc.buy, "ASML.AS", 2, 600))
    assert depot["watchlist"] == [] and depot["positions"][0]["quantity"] == 2
    assert any("removed from the Watchlist" in n for n in notes)


def test_buy_more_averages_entry_price():
    depot, _ = depot_with((dc.add_position, "SAP.DE", 10, 180), (dc.buy, "SAP.DE", 5, 210))
    pos = depot["positions"][0]
    assert pos["quantity"] == 15 and pos["entry_price"] == pytest.approx(190)


def test_buy_without_price_makes_average_unknown():
    depot, notes = depot_with((dc.add_position, "SAP.DE", 10, 180), (dc.buy, "SAP.DE", 5))
    assert depot["positions"][0]["entry_price"] is None
    assert any("unknown" in n for n in notes)


def test_buy_in_other_currency_is_rejected():
    depot, _ = depot_with((dc.add_position, "AAPL", 1, 190, "EUR"))
    with pytest.raises(dc.DepotError, match="bought in EUR"):
        dc.buy(depot, "AAPL", 1, 200, "USD")


def test_sell_part_keeps_entry_price_and_sell_all_removes():
    depot, _ = depot_with((dc.add_position, "SAP.DE", 10, 180), (dc.sell, "SAP.DE", 4))
    assert depot["positions"][0]["quantity"] == 6 and depot["positions"][0]["entry_price"] == 180
    depot, notes = dc.sell(depot, "SAP.DE", 6)
    assert depot["positions"] == [] and notes
    with pytest.raises(dc.DepotError, match="only 2 held"):
        dc.sell(depot_with((dc.add_position, "X", 2))[0], "X", 3)


def test_sell_without_quantity_removes_position():
    depot, _ = depot_with((dc.add_position, "SAP.DE", 10), (dc.sell, "SAP.DE", None))
    assert depot["positions"] == []


def test_watchlist_rules():
    depot, _ = depot_with((dc.add_position, "SAP.DE", 1))
    with pytest.raises(dc.DepotError, match="already a Position"):
        dc.watch(depot, "SAP.DE")
    depot, _ = dc.watch(depot, "ASML.AS", note="wait for a dip")
    with pytest.raises(dc.DepotError, match="already on the Watchlist"):
        dc.watch(depot, "asml.as")
    depot, _ = dc.unwatch(depot, "ASML.AS")
    assert depot["watchlist"] == []


def test_update_position():
    depot, _ = depot_with((dc.add_position, "SAP.DE", 10, 180), (dc.update_position, "SAP.DE"))
    depot, _ = dc.update_position(depot, "SAP.DE", entry_price=175.5, name="SAP SE")
    assert depot["positions"][0]["entry_price"] == 175.5 and depot["positions"][0]["quantity"] == 10
    with pytest.raises(dc.DepotError, match="not in the Depot"):
        dc.update_position(depot, "AAPL", quantity=1)


# --- valuation ---------------------------------------------------------------------------------


def test_value_depot_converts_currencies_and_weights():
    depot, _ = depot_with(
        (dc.add_position, "SAP.DE", 10, 180),          # EUR
        (dc.add_position, "AAPL", 5, 300, "EUR"),      # bought in EUR on a German venue, quoted in USD
    )
    quotes = {"SAP.DE": {"price": 210, "currency": "EUR"}, "AAPL": {"price": 360, "currency": "USD"}}
    valuation, warnings = dc.value_depot(depot, quotes, {"USD": 0.9})
    sap, aapl = valuation["positions"]
    assert sap["value_base"] == 2100 and sap["pnl_base"] == 300 and sap["pnl_pct"] == pytest.approx(16.67)
    assert aapl["value_base"] == 1620 and aapl["cost_base"] == 1500 and aapl["pnl_base"] == 120
    assert valuation["summary"]["total_value_base"] == 3720
    assert sap["weight_pct"] + aapl["weight_pct"] == pytest.approx(100)
    assert any("Concentration" in w for w in warnings)  # both are above 25 %
    assert not any("exchange-rate moves" in w for w in warnings)  # entry was in EUR, no FX caveat


def test_concentration_ignores_etfs_and_partial_pnl_is_flagged():
    depot, _ = depot_with((dc.add_position, "EUNL.DE", 20), (dc.add_position, "SAP.DE", 1, 180))
    quotes = {"EUNL.DE": {"price": 130, "currency": "EUR", "type": "ETF"},
              "SAP.DE": {"price": 210, "currency": "EUR", "type": "EQUITY"}}
    valuation, warnings = dc.value_depot(depot, quotes, {})
    assert valuation["positions"][0]["weight_pct"] > 90
    assert not any("EUNL.DE" in w and "Concentration" in w for w in warnings)
    assert valuation["summary"]["pnl_positions"] == 1
    assert any("covers only 1 of 2" in w for w in warnings)


def test_value_depot_pence_and_fx_caveat():
    depot, _ = depot_with((dc.add_position, "SHEL.L", 100, 25, "GBP"))
    quotes = {"SHEL.L": {"price": 2700, "currency": "GBp"}}  # 2700 pence = 27 GBP
    valuation, warnings = dc.value_depot(depot, quotes, {"GBP": 1.15})
    row = valuation["positions"][0]
    assert row["price"] == 27 and row["price_currency"] == "GBP"
    assert row["value_base"] == pytest.approx(3105) and row["pnl_pct"] == pytest.approx(8.0)
    assert any("exchange-rate moves" in w for w in warnings)


def test_value_depot_missing_data_is_reported_not_guessed():
    depot, _ = depot_with((dc.add_position, "A", 1, 10), (dc.add_position, "B"), (dc.add_position, "C", 1))
    quotes = {"A": {"price": 12, "currency": "EUR"}, "B": {"price": 5, "currency": "EUR"}, "C": {"price": 7, "currency": "CHF"}}
    valuation, warnings = dc.value_depot(depot, quotes, {})
    a, b, c = valuation["positions"]
    assert a["weight_pct"] == 100
    assert b["value_base"] is None and c["value_base"] is None
    assert any("Quantity of B unknown" in w for w in warnings)
    assert any("No exchange rate CHF->EUR" in w for w in warnings)
    assert valuation["summary"]["valued_positions"] == 1


# --- snapshot ----------------------------------------------------------------------------------


def test_snapshot_lists_everything_and_marks_unknowns():
    depot, _ = depot_with(
        (dc.add_position, "SAP.DE", 10, 180, None, "SAP SE"),
        (dc.add_position, "AAPL"),
        (dc.watch, "ASML.AS", "ASML Holding", "wait for a dip"),
    )
    text = dc.render_snapshot(depot, "2026-11-15")
    assert text.startswith(dc.SNAPSHOT_HEADER) and "as of 2026-11-15" in text
    assert "- SAP.DE | SAP SE | qty 10 | entry 180 EUR" in text
    assert "- AAPL | ? | qty ? | entry ?" in text
    assert "- ASML.AS | ASML Holding | note: wait for a dip" in text
    assert text.rstrip().endswith("END SNAPSHOT")


def test_snapshot_of_empty_depot():
    text = dc.render_snapshot(dc.empty_depot(), "2026-11-15")
    assert text.count("(none)") == 2


# --- CLI round trip ----------------------------------------------------------------------------


def test_cli_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCIAL_SUPPORT_HOME", str(tmp_path))
    import depot as cli

    assert cli.run(["add", "SAP.DE", "--quantity", "10", "--entry-price", "180"])["ok"]
    assert cli.run(["watch", "ASML.AS"])["ok"]
    bad = cli.run(["sell", "SAP.DE", "--quantity", "50"])
    assert not bad["ok"] and "only 10 held" in bad["error"]
    saved = json.loads((tmp_path / "depot.json").read_text())
    assert saved["positions"][0]["quantity"] == 10 and saved["watchlist"][0]["symbol"] == "ASML.AS"
    assert "SAP.DE" in cli.run(["snapshot"])["snapshot"]
