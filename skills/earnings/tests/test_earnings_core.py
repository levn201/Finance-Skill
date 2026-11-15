import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import earnings_core as ec  # noqa: E402

TODAY = date(2026, 11, 15)
ROWS = [
    {"date": "2027-01-28", "eps_estimate": 1.98, "eps_reported": None, "surprise_pct": None},
    {"date": "2026-10-20", "eps_estimate": 1.83, "eps_reported": 1.89, "surprise_pct": 3.09},
    {"date": "2026-07-22", "eps_estimate": 1.75, "eps_reported": 1.59, "surprise_pct": -9.29},
    {"date": "2026-04-23", "eps_estimate": 1.66, "eps_reported": 1.72, "surprise_pct": 3.66},
    {"date": "2025-01-01", "eps_estimate": 1.0, "eps_reported": None, "surprise_pct": None},  # past, never reported
]
CLOSES = [("2026-04-22", 100.0), ("2026-04-24", 104.0), ("2026-07-21", 110.0), ("2026-07-23", 99.0),
          ("2026-10-17", 120.0), ("2026-10-21", 117.6)]


def test_split_dates():
    reported, upcoming = ec.split_dates(ROWS, TODAY)
    assert [r["date"] for r in reported] == ["2026-10-20", "2026-07-22", "2026-04-23"]
    assert [r["date"] for r in upcoming] == ["2027-01-28"]  # an old unreported row is not "upcoming"


def test_price_reaction_window_and_gaps():
    assert ec.price_reaction(CLOSES, "2026-04-23") == {"from": "2026-04-22", "to": "2026-04-24", "move_pct": 4.0}
    assert ec.price_reaction(CLOSES, "2026-10-20")["move_pct"] == -2.0
    assert ec.price_reaction(CLOSES, "2030-01-01") is None
    assert ec.price_reaction([("2026-01-01", 1.0), ("2026-02-01", 2.0)], "2026-01-15") is None  # gap > 7 days


def test_track_record():
    reported, _ = ec.split_dates(ROWS, TODAY)
    tr = ec.track_record(reported, CLOSES)
    assert tr["beat_rate_pct"] == 67 and tr["avg_surprise_pct"] == round((3.09 - 9.29 + 3.66) / 3, 2)
    assert tr["avg_abs_move_pct"] == round((2.0 + 10.0 + 4.0) / 3, 2) and tr["max_abs_move_pct"] == 10.0
    assert tr["beat_but_fell"] == ["2026-10-20"]  # beat by 3 % and still fell 2 %
    assert ec.track_record([], [])["beat_rate_pct"] is None


def test_consensus_and_revision():
    est = {
        "eps": [{"index": "0q", "avg": 1.98, "low": 1.9, "high": 2.18, "numberOfAnalysts": 10, "yearAgoEps": 1.62, "growth": 0.2225, "currency": "EUR"},
                {"index": "0y", "avg": 7.16, "low": 6.6, "high": 7.98, "numberOfAnalysts": 24, "yearAgoEps": 6.15, "growth": 0.1647, "currency": "EUR"}],
        "revenue": [{"index": "0q", "avg": 1.07e10, "low": 1.06e10, "high": 1.1e10, "numberOfAnalysts": 13, "yearAgoRevenue": 9.68e9, "growth": 0.1115, "currency": "EUR"}],
        "eps_trend": [{"index": "0q", "current": 1.98, "30daysAgo": 2.033, "90daysAgo": 2.033}],
    }
    c = ec.consensus(est)
    assert c["quarter_eps"]["avg"] == 1.98 and c["quarter_eps"]["growth_pct"] == 22.25
    assert c["quarter_revenue"]["analysts"] == 13 and c["year_revenue"] is None
    assert c["eps_revision"]["direction"] == "down" and c["eps_revision"]["change_90d_pct"] < -2
    assert ec.consensus({})["eps_revision"] is None


def test_default_mode():
    reported, _ = ec.split_dates(ROWS, TODAY)
    assert ec.default_mode(reported, TODAY) == "preview"
    assert ec.default_mode(reported, date(2026, 10, 25)) == "review"
    assert ec.default_mode([], TODAY) == "preview"
