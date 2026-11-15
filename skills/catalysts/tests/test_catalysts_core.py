import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import catalysts_core as cc  # noqa: E402

TODAY = date(2026, 11, 15)
CONTEXT = {"SAP.DE": {"name": "SAP SE", "in": "depot"}, "AAPL": {"name": "Apple", "in": "depot"},
           "ASML.AS": {"name": "ASML", "in": "watchlist"}}
PER_SYMBOL = {
    "SAP.DE": {"events": [{"type": "earnings", "date": "2026-10-21", "status": "past", "source": "Yahoo"}],
               "warnings": ["No confirmed upcoming earnings date; ...", "AGM dates are not provided by these data sources; ..."]},
    "AAPL": {"events": [{"type": "earnings", "date": "2027-01-28", "status": "upcoming", "estimated": True, "source": "Yahoo"},
                        {"type": "ex_dividend", "date": "2026-11-12", "status": "past", "source": "Yahoo"}], "warnings": []},
    "ASML.AS": {"events": [{"type": "earnings", "date": "2026-11-20", "status": "upcoming", "estimated": False, "source": "Finnhub"}],
                "warnings": []},
}
ECB = {"date": "2026-12-17", "type": "central_bank", "symbol": None, "title": "ECB monetary policy meeting",
       "source": "European Central Bank", "url": "https://www.ecb.europa.eu"}


def test_calendar_sorted_filtered_and_flagged():
    cal = cc.build_calendar(PER_SYMBOL, CONTEXT, cc.validate_extra([ECB]), TODAY, 90)
    assert [(e["date"], e["symbol"] or e["title"]) for e in cal["events"]] == [
        ("2026-11-20", "ASML.AS"), ("2026-12-17", "ECB monetary policy meeting"), ("2027-01-28", "AAPL")]
    asml = cal["events"][0]
    assert asml["critical"] and asml["in_days"] == 5 and asml["in"] == "watchlist" and asml["name"] == "ASML"
    assert not cal["events"][1]["critical"]
    assert cal["critical_count"] == 1
    assert cal["no_upcoming_earnings"] == ["SAP.DE"]


def test_past_events_and_events_beyond_window_are_dropped():
    cal = cc.build_calendar(PER_SYMBOL, CONTEXT, [], TODAY, 30)
    assert [e["symbol"] for e in cal["events"]] == ["ASML.AS"]


def test_agm_warning_said_once_and_symbol_warnings_prefixed():
    cal = cc.build_calendar(PER_SYMBOL, CONTEXT, [], TODAY, 90)
    assert sum("AGM" in w for w in cal["warnings"]) == 1
    assert any(w.startswith("SAP.DE: No confirmed upcoming") for w in cal["warnings"])


def test_empty_inputs():
    cal = cc.build_calendar({}, {}, [], TODAY, 90)
    assert cal["events"] == [] and cal["warnings"] == []


@pytest.mark.parametrize("change, message", [
    ({"date": "17.12.2026"}, "ISO date"),
    ({"type": "party"}, "type must be one of"),
    ({"title": " "}, "needs a title"),
    ({"url": ""}, "source and url"),
])
def test_extra_events_need_date_type_title_and_source(change, message):
    with pytest.raises(cc.CatalystError, match=message):
        cc.validate_extra([{**ECB, **change}])


def test_extra_agm_gets_symbol_context():
    agm = {"date": "2026-12-01", "type": "agm", "symbol": "sap.de", "title": "SAP AGM", "source": "SAP IR", "url": "https://sap.com"}
    cal = cc.build_calendar({}, CONTEXT, cc.validate_extra([agm]), TODAY, 90)
    assert cal["events"][0]["symbol"] == "SAP.DE" and cal["events"][0]["in"] == "depot"


def test_diff_new_moved_gone():
    old = [{"symbol": "AAPL", "type": "earnings", "title": None, "date": "2027-01-28"},
           {"symbol": "ASML.AS", "type": "earnings", "title": None, "date": "2026-11-20"},
           {"symbol": "SAP.DE", "type": "ex_dividend", "title": None, "date": "2027-05-01"}]
    new = [{"symbol": "AAPL", "type": "earnings", "title": None, "date": "2027-01-29"},
           {"symbol": None, "type": "central_bank", "title": "ECB", "date": "2026-12-17"}]
    d = cc.diff_calendars(old, new, date(2026, 11, 21))
    assert d["moved"] == [{"symbol": "AAPL", "type": "earnings", "title": None, "from": "2027-01-28", "to": "2027-01-29"}]
    assert [e["title"] for e in d["new"]] == ["ECB"]
    assert [e["symbol"] for e in d["gone"]] == ["SAP.DE"]  # ASML just passed, so it's not "gone"
    assert [e["symbol"] for e in cc.diff_calendars(old, new, TODAY)["gone"]] == ["ASML.AS", "SAP.DE"]
    assert cc.diff_calendars(None, new, TODAY)["first"]
