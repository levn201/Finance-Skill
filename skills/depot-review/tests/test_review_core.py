import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import review_core as rc  # noqa: E402

TODAY = date(2026, 11, 15)
LAST = {"created_at": "2026-11-12T10:00:00+00:00"}


def test_close_on():
    rows = [("2026-11-10", 100.0), ("2026-11-11", 101.0), ("2026-11-13", 103.0)]
    assert rc.close_on(rows, "2026-11-12") == 101.0
    assert rc.close_on(rows, "2026-11-09") is None


@pytest.mark.parametrize("last, now, then, earnings, reuse, reason", [
    (None, 100, 100, [], False, "no previous"),
    ({"created_at": "2026-11-01T10:00:00+00:00"}, 100, 100, [], False, "14 days old"),
    (LAST, 100, 100, ["2026-11-14"], False, "results were published"),
    (LAST, 100, 100, ["2026-11-12"], True, "no results since"),   # same day as the Assessment: already known
    (LAST, 100, 100, ["2026-11-20"], True, "no results since"),   # upcoming results don't block reuse
    (LAST, 112, 100, [], False, "moved +12.0%"),
    (LAST, None, 100, [], False, "unknown"),
    (LAST, 104, 100, [], True, "+4.0%"),
])
def test_reuse_decision(last, now, then, earnings, reuse, reason):
    d = rc.reuse_decision(last, TODAY, now, then, earnings)
    assert d["reuse"] is reuse and reason in d["reason"]


def item(symbol, where, view, confidence="medium"):
    return {"symbol": symbol, "in": where, "view": view, "confidence": confidence, "reason": "r", "reused": False}


def test_rank_puts_sells_first_in_depot_and_buys_first_on_watchlist():
    ranked = rc.rank([
        item("HOLD1", "depot", "hold"), item("BUY1", "depot", "buy"), item("SELL1", "depot", "sell", "low"),
        item("SELL2", "depot", "sell", "high"), item("W_WAIT", "watchlist", "hold"), item("W_BUY", "watchlist", "buy"),
        item("W_NO", "watchlist", "sell"),
    ])
    assert [r["symbol"] for r in ranked] == ["SELL2", "SELL1", "BUY1", "HOLD1", "W_BUY", "W_WAIT", "W_NO"]
    assert [r["label"] for r in ranked][:4] == ["Verkaufen", "Verkaufen", "Nachkaufen", "Halten"]
    assert ranked[-1]["label"] == "Nicht kaufen" and ranked[-1]["rank"] == 7


EXPECTED = {"SAP.DE": "depot", "ASML.AS": "watchlist"}


def review(*items, summary="ok"):
    return {"summary": summary, "items": list(items)}


def test_validate_accepts_complete_review():
    rc.validate_review(review(item("SAP.DE", "depot", "hold"), item("ASML.AS", "watchlist", "buy")), EXPECTED)


@pytest.mark.parametrize("data, message", [
    (review(item("SAP.DE", "depot", "hold")), "missing from the review: ASML.AS"),
    (review(item("SAP.DE", "depot", "hold"), item("ASML.AS", "watchlist", "buy"), item("X", "depot", "buy")), "not in Depot"),
    (review(item("SAP.DE", "depot", "hold"), item("SAP.DE", "depot", "hold")), "appears twice"),
    (review(item("SAP.DE", "depot", "strong buy"), item("ASML.AS", "watchlist", "buy")), "view must be"),
    (review(item("SAP.DE", "watchlist", "hold"), item("ASML.AS", "watchlist", "buy")), "'in' must be 'depot'"),
    (review(item("SAP.DE", "depot", "hold"), item("ASML.AS", "watchlist", "buy"), summary=""), "summary"),
    (review({**item("SAP.DE", "depot", "hold"), "reason": " "}, item("ASML.AS", "watchlist", "buy")), "one-line reason"),
])
def test_validate_rejects(data, message):
    with pytest.raises(rc.ReviewError, match=message):
        rc.validate_review(data, EXPECTED)


def test_diff_reviews():
    old = review(item("SAP.DE", "depot", "hold"), item("OLD", "depot", "sell"))
    new = review(item("SAP.DE", "depot", "sell"), item("ASML.AS", "watchlist", "buy"))
    d = rc.diff_reviews(old, new)
    assert d["changes"] == [{"symbol": "SAP.DE", "from": "hold", "to": "sell", "in": "depot"}]
    assert d["added"] == ["ASML.AS"] and d["removed"] == ["OLD"]
    assert rc.diff_reviews(None, new)["first"]
