import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import journal as jr  # noqa: E402

SRC = {"name": "Yahoo Finance (via yfinance)", "url": "https://finance.yahoo.com/quote/SAP.DE", "retrieved_at": "2026-11-15T10:00:00+00:00"}
ASSESSMENT = {
    "symbol": "SAP.DE",
    "name": "SAP SE",
    "view": "hold",
    "context": "position",
    "horizon_basis": "medium-term",
    "confidence": "medium",
    "thesis_verdict": "intact",
    "outlooks": {
        "short-term": {"direction": "uncertain", "summary": "Swings possible from AI competition headlines", "drivers": ["Competition"]},
        "medium-term": {"direction": "positive", "summary": "Cloud growth carries margins", "drivers": ["Cloud growth 27 %"]},
    },
    "reasons_for": ["Cloud growth 27 %"],
    "reasons_against": ["P/E 31 above 5y average"],
    "invalidation": ["Cloud growth below 15 % for two quarters"],
    "key_figures": [{"label": "P/E", "value": 30.9, "source": "Yahoo", "as_of": "2026-11-15"}],
    "sources": [SRC],
    "lite_mode": False,
}


def entry(**changes):
    data = deepcopy(ASSESSMENT)
    for key, value in changes.items():
        data[key] = value
    return {"subject": "sap.de", "data": data, "report_markdown": "# SAP"}


def at(day, hour=10):
    return datetime(2026, 11, day, hour, tzinfo=timezone.utc)


def test_first_save_has_no_previous(tmp_path):
    saved, diff = jr.save_entry(tmp_path, "assessment", entry(), at(15))
    assert diff == {"first": True, "changes": []}
    assert Path(saved["path"]).parent.name == "2026-11-15" and saved["subject"] == "SAP.DE"


def test_second_save_reports_changes(tmp_path):
    jr.save_entry(tmp_path, "assessment", entry(), at(10))
    outlooks = deepcopy(ASSESSMENT["outlooks"])
    outlooks["short-term"]["direction"] = "negative"
    _, diff = jr.save_entry(tmp_path, "assessment", entry(view="sell", outlooks=outlooks, thesis_verdict="broken"), at(15))
    assert diff["days_since"] == 5
    assert {c["field"] for c in diff["changes"]} == {"view", "outlook.short-term", "thesis_verdict"}
    assert {"field": "view", "from": "hold", "to": "sell"} in diff["changes"]


def test_same_second_saves_do_not_overwrite(tmp_path):
    a, _ = jr.save_entry(tmp_path, "assessment", entry(), at(15))
    b, _ = jr.save_entry(tmp_path, "assessment", entry(), at(15))
    assert a["path"] != b["path"] and len(jr.load_entries(tmp_path, "assessment", "SAP.DE")) == 2


@pytest.mark.parametrize("changes, message", [
    ({"view": "strong buy"}, "view must be one of"),
    ({"outlooks": {"medium-term": ASSESSMENT["outlooks"]["medium-term"]}}, "one entry per Horizon"),
    ({"reasons_against": []}, "reasons_against needs at least 1"),
    ({"invalidation": []}, "invalidation needs at least 1"),
    ({"sources": []}, "sources needs at least 1"),
    ({"sources": [{"name": "x"}]}, "retrieved_at or as_of"),
    ({"key_figures": [{"label": "P/E", "value": 30}]}, "needs a source"),
    ({"extra": {"position_size": "10 %"}}, "never include position sizes"),
])
def test_invalid_assessments_are_rejected_and_not_stored(tmp_path, changes, message):
    with pytest.raises(jr.JournalError, match=message):
        jr.save_entry(tmp_path, "assessment", entry(**changes), at(15))
    assert jr.load_entries(tmp_path, "assessment", "SAP.DE") == []


def test_unknown_kind_is_stored_without_assessment_validation(tmp_path):
    saved, diff = jr.save_entry(tmp_path, "market-brief", {"subject": "global", "data": {"anything": 1}}, at(15))
    assert diff == {"first": True} and saved["kind"] == "market-brief"


def test_unknown_figure_without_value_is_allowed(tmp_path):
    jr.save_entry(tmp_path, "assessment", entry(key_figures=[{"label": "Next earnings", "value": None}]), at(15))


def test_cli(tmp_path):
    env = {"FINANCIAL_SUPPORT_HOME": str(tmp_path)}
    r = jr.run(["save", "assessment"], json.dumps(entry()), env)
    assert r["ok"] and r["diff"]["first"]
    assert jr.run(["last", "assessment", "SAP.DE"], environ=env)["entry"]["data"]["view"] == "hold"
    assert len(jr.run(["history", "assessment", "sap.de"], environ=env)["entries"]) == 1
    assert not jr.run(["save", "assessment"], "not json", env)["ok"]
    assert jr.run(["last", "assessment", "AAPL"], environ=env)["entry"] is None


def test_input_file_taken_and_consumed_only_from_inbox(tmp_path):
    inbox = tmp_path / jr.INBOX_DIR
    inbox.mkdir()
    f = inbox / "assessment.json"
    f.write_text('{"a": 1}', encoding="utf-8")
    argv, text, path = jr.take_input(["save", "assessment", "--input", str(f)])
    assert argv == ["save", "assessment"] and text == '{"a": 1}' and path == f
    outside = tmp_path / "elsewhere.json"
    outside.write_text("[]", encoding="utf-8")
    jr.consume_input(tmp_path, outside)
    assert outside.exists()                      # never deletes outside the inbox
    jr.consume_input(tmp_path, f)
    assert not f.exists()
    assert jr.take_input(["show"]) == (["show"], None, None)
    with pytest.raises(jr.JournalError):
        jr.take_input(["save", "x", "--input"])
    with pytest.raises(jr.JournalError):
        jr.take_input(["save", "x", "--input", str(tmp_path / "missing.json")])
