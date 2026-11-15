import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import daily_core as dc  # noqa: E402

MON, TUE, SAT = date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 14)


def test_should_run():
    assert dc.should_run(TUE, None) == (True, "ok")
    assert dc.should_run(SAT, None) == (False, "weekend")
    assert dc.should_run(TUE, "2026-11-17T06:31:00+00:00") == (False, "already ran today")
    assert dc.should_run(TUE, "2026-11-16T06:31:00+00:00")[0]


def test_review_due_reasons():
    recent = "2026-11-15T15:00:00+00:00"
    assert dc.review_due(TUE, recent, {"SAP.DE": 1.2}, {"SAP.DE": "2026-10-20"}) == (False, [])
    due, why = dc.review_due(MON, recent, {}, {})
    assert due and why == ["Monday"]
    assert dc.review_due(TUE, None, {}, {})[1] == ["no Depot Review yet"]
    assert "older than" in dc.review_due(TUE, "2026-11-05T08:00:00+00:00", {}, {})[1][0]
    due, why = dc.review_due(TUE, recent, {"ASML.AS": -6.3, "AAPL": None, "SAP.DE": 4.9}, {})
    assert why == ["ASML.AS moved -6.3 % yesterday"]
    due, why = dc.review_due(TUE, recent, {}, {"AAPL": "2026-11-14", "SAP.DE": "2026-11-10", "X": None})
    assert why == ["AAPL reported results on 2026-11-14"]


def test_late_run():
    assert dc.is_late(datetime(2026, 11, 17, 23, 0)) and not dc.is_late(datetime(2026, 11, 17, 7, 35))


def _report(**over):
    base = {"headline": "Ruhiger Tag", "language": "de", "regime": "normal", "changes": [],
            "upcoming": [{"date": "2026-11-18", "symbol": "NVDA", "event": "Zahlen"}], "actions": [],
            "depot_review": {"ran": False, "reasons": []}}
    return {**base, **over}


def test_validate_report():
    dc.validate_report(_report())
    for bad in ({"headline": ""}, {"headline": "x" * 201}, {"changes": None}, {"upcoming": [{"date": "2026-11-18"}]},
                {"depot_review": {}}, {"language": None}, {"actions": "none"}):
        with pytest.raises(dc.DailyError):
            dc.validate_report(_report(**bad))


def test_diff_and_critical_soon():
    assert dc.diff_reports(None, _report()) == {"first": True}
    prev = _report(regime="calm", actions=["SAP prüfen"])
    cur = _report(actions=["ASML prüfen"], upcoming=[{"date": "2026-11-18", "symbol": "NVDA", "event": "Zahlen"},
                                                     {"date": "2026-11-25", "symbol": "SAP.DE", "event": "HV"}])
    d = dc.diff_reports(prev, cur)
    assert d["regime"] == {"from": "calm", "to": "normal"}
    assert d["new_actions"] == ["ASML prüfen"] and d["dropped_actions"] == ["SAP prüfen"]
    assert [u["symbol"] for u in d["new_upcoming"]] == ["SAP.DE"]
    assert [u["symbol"] for u in dc.critical_soon(cur["upcoming"], TUE)] == ["NVDA"]
