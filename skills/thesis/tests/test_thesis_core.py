import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import thesis_core as tc  # noqa: E402

PILLARS = ["Cloud revenue keeps growing > 20 %", "Operating margin expands", "AI features drive upsell"]
TRIGGERS = ["Cloud growth below 15 % for two quarters"]


def recorded():
    return tc.record(tc.empty_store(), "sap.de", "SAP shifts to high-margin cloud", PILLARS, TRIGGERS, name="SAP SE")


def test_record_creates_unchecked_thesis_with_numbered_pillars():
    t = recorded()["theses"]["SAP.DE"]
    assert t["status"] == "active" and t["verdict"] == "unchecked"
    assert [p["id"] for p in t["pillars"]] == [1, 2, 3] and all(p["status"] == "open" for p in t["pillars"])
    assert t["horizon"] == "medium-term" and t["conviction"] == "medium"
    assert t["log"][0]["kind"] == "recorded"


@pytest.mark.parametrize("kwargs, message", [
    ({"statement": " "}, "statement must not be empty"),
    ({"pillars": []}, "1 to 5 pillars"),
    ({"pillars": ["a"] * 6}, "1 to 5 pillars"),
    ({"exit_triggers": []}, "exit trigger"),
    ({"horizon": "forever"}, "horizon must be one of"),
])
def test_record_validates(kwargs, message):
    args = {"statement": "s", "pillars": PILLARS, "exit_triggers": TRIGGERS, **kwargs}
    with pytest.raises(tc.ThesisError, match=message):
        tc.record(tc.empty_store(), "SAP.DE", **args)


def test_record_twice_requires_revise():
    with pytest.raises(tc.ThesisError, match="use revise"):
        tc.record(recorded(), "SAP.DE", "x", ["y"], ["z"])


def test_revise_keeps_previous_version():
    store = tc.revise(recorded(), "SAP.DE", "AI is now the main driver", statement="SAP becomes the AI layer for ERP")
    t = store["theses"]["SAP.DE"]
    assert t["statement"] == "SAP becomes the AI layer for ERP"
    assert t["log"][-1]["kind"] == "revised"
    assert t["log"][-1]["previous"]["statement"] == "SAP shifts to high-margin cloud"
    assert t["pillars"][0]["text"] == PILLARS[0]  # untouched fields stay


def test_log_data_point_with_pillar_impacts():
    store = tc.log_data_point(recorded(), "SAP.DE", "Q3 cloud growth 27 %", ["1=strengthens"], ["https://ir.sap.com"], "2026-10-21")
    entry = store["theses"]["SAP.DE"]["log"][-1]
    assert entry == {"date": "2026-10-21", "kind": "data_point", "text": "Q3 cloud growth 27 %",
                     "pillar_impacts": {"1": "strengthens"}, "sources": ["https://ir.sap.com"]}
    with pytest.raises(tc.ThesisError, match="no pillar 9"):
        tc.log_data_point(recorded(), "SAP.DE", "x", ["9=weakens"])
    with pytest.raises(tc.ThesisError, match="impact must be one of"):
        tc.log_data_point(recorded(), "SAP.DE", "x", ["1=great"])


def test_check_updates_pillars_verdict_and_conviction():
    store = tc.check(recorded(), "SAP.DE", "weakened", "Margins flat", ["1=holds", "2=at-risk"], "low", ["https://x"])
    t = store["theses"]["SAP.DE"]
    assert t["verdict"] == "weakened" and t["conviction"] == "low" and t["last_checked_at"]
    assert [p["status"] for p in t["pillars"]] == ["holds", "at-risk", "open"]
    assert t["log"][-1]["pillars"] == {"1": "holds", "2": "at-risk", "3": "open"}


def test_broken_verdict_needs_evidence():
    with pytest.raises(tc.ThesisError, match="broken verdict needs"):
        tc.check(recorded(), "SAP.DE", "broken", "feels bad")
    assert tc.check(recorded(), "SAP.DE", "broken", "Cloud growth 12 %", ["1=broken"])["theses"]["SAP.DE"]["verdict"] == "broken"


def test_archive_then_new_thesis_keeps_history():
    store = tc.archive(recorded(), "SAP.DE", "sold")
    assert store["theses"]["SAP.DE"]["status"] == "archived"
    with pytest.raises(tc.ThesisError, match="no active Thesis"):
        tc.check(store, "SAP.DE", "intact", "x")
    store = tc.record(store, "SAP.DE", "Re-entry: valuation reset", ["Cheaper than peers"], ["Growth stalls"])
    kinds = [e["kind"] for e in store["theses"]["SAP.DE"]["log"]]
    assert kinds == ["recorded", "archived", "recorded"]


def test_gaps():
    store = recorded()
    store = tc.record(store, "OLD", "x", ["y"], ["z"])
    depot = {"positions": [{"symbol": "SAP.DE"}, {"symbol": "AAPL", "name": "Apple"}],
             "watchlist": [{"symbol": "ASML.AS", "name": "ASML"}]}
    store["theses"]["SAP.DE"]["created_at"] = "2026-01-01T00:00:00+00:00"
    g = tc.gaps(store, depot, date(2026, 11, 15))
    assert g["missing"] == [{"symbol": "AAPL", "name": "Apple", "in": "depot"},
                            {"symbol": "ASML.AS", "name": "ASML", "in": "watchlist"}]
    assert g["due_for_review"] == [{"symbol": "SAP.DE", "days_since_check": 318, "never_checked": True}]
    assert g["not_in_depot_or_watchlist"] == [{"symbol": "OLD"}]


def test_cli_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCIAL_SUPPORT_HOME", str(tmp_path))
    import thesis as cli

    r = cli.run(["record", "SAP.DE", "--statement", "cloud", "--pillar", "growth", "--exit-trigger", "slowdown"])
    assert r["ok"] and r["thesis"]["symbol"] == "SAP.DE"
    assert not cli.run(["log", "SAP.DE", "--text", "x", "--date", "not-a-date"])["ok"]
    assert cli.run(["check", "SAP.DE", "--verdict", "intact", "--summary", "fine", "--pillar-status", "1=holds"])["ok"]
    saved = json.loads((tmp_path / "theses.json").read_text())
    assert saved["theses"]["SAP.DE"]["verdict"] == "intact"
    assert cli.run(["show"])["theses"][0]["pillars"] == ["1. growth [holds]"]
    assert cli.run(["gaps"])["warnings"]
