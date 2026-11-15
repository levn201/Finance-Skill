import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import brief_core as bc  # noqa: E402


def rows(values):
    return [(f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", v) for i, v in enumerate(values)]


def test_indicator_summary():
    s = bc.indicator_summary(rows([100.0] * 30 + [110.0]))
    assert s["last"] == 110 and s["change_1d_pct"] == 10.0 and s["change_1w_pct"] == 10.0
    assert s["percentile_1y"] == 100 and s["range_1y"] == [100, 110]
    assert s["above_sma200"] is None  # fewer than 200 points
    assert bc.indicator_summary(rows([1.0])) is None


def test_indicator_summary_sma200():
    s = bc.indicator_summary(rows([100.0] * 199 + [50.0]))
    assert s["above_sma200"] is False
    assert s["percentile_1y"] <= 1  # the lowest value of the year


@pytest.mark.parametrize("vix, regime", [(12, "calm"), (15, "normal"), (19.3, "normal"), (25, "elevated"), (30, "stress"), (None, None)])
def test_vix_regime(vix, regime):
    assert bc.vix_regime(vix) == regime


def test_yield_curve():
    assert bc.yield_curve(5.15, 4.12) == {"spread_10y_3m_pct_points": 1.03, "inverted": False}
    assert bc.yield_curve(3.9, 4.5)["inverted"] is True
    assert bc.yield_curve(None, 4.5) is None


def test_exposure_weights_and_etfs():
    items = [
        {"symbol": "SAP.DE", "sector": "Technology", "country": "Germany", "currency": "EUR", "type": "EQUITY"},
        {"symbol": "AAPL", "sector": "Technology", "country": "United States", "currency": "USD", "type": "EQUITY"},
        {"symbol": "EUNL.DE", "sector": None, "country": None, "currency": "EUR", "type": "ETF"},
        {"symbol": "X", "sector": "Energy", "country": "US", "currency": "USD", "type": "EQUITY"},
    ]
    e = bc.exposure(items, {"SAP.DE": 40.0, "AAPL": 30.0, "EUNL.DE": 30.0, "X": None})
    assert e["sector"] == {"Technology": 70.0, "ETF / diversified": 30.0}
    assert e["currency"] == {"EUR": 70.0, "USD": 30.0}
    assert e["country"]["ETF / diversified"] == 30.0
    assert e["not_weighted"] == ["X"]


SRC = [{"name": "Reuters", "url": "https://reuters.com/x", "as_of": "2026-11-14"}]
THEME = {"title": "US tariffs on semiconductors", "category": "trade", "direction": "negative", "affects": ["ASML.AS"], "sources": SRC}


def brief(**changes):
    return {"regime": "normal", "indicators": {"^VIX": {"last": 19.3}}, "themes": [THEME],
            "depot_impact": "ASML on the Watchlist is directly exposed.", **changes}


def test_validate_brief_ok():
    bc.validate_brief(brief())


@pytest.mark.parametrize("changes, message", [
    ({"regime": "panic"}, "regime must be"),
    ({"themes": []}, "at least one"),
    ({"themes": [{**THEME, "category": "gossip"}]}, "category must be"),
    ({"themes": [{**THEME, "direction": "up"}]}, "direction must be"),
    ({"themes": [{**THEME, "sources": []}]}, "needs at least one source"),
    ({"themes": [{**THEME, "affects": "ASML"}]}, "affects must be a list"),
    ({"depot_impact": " "}, "depot_impact"),
])
def test_validate_brief_rejects(changes, message):
    with pytest.raises(bc.BriefError, match=message):
        bc.validate_brief(brief(**changes))


def test_diff_briefs():
    old = brief()
    new = brief(regime="elevated", indicators={"^VIX": {"last": 24.0}},
                themes=[{**THEME, "direction": "uncertain"}, {**THEME, "title": "ECB cuts rates", "category": "central_banks"}])
    d = bc.diff_briefs(old, new)
    assert d["regime"] == {"from": "normal", "to": "elevated"} and d["vix"] == {"from": 19.3, "to": 24.0}
    assert d["new_themes"] == ["ECB cuts rates"] and d["dropped_themes"] == []
    assert d["direction_changes"] == [{"title": "US tariffs on semiconductors", "from": "negative", "to": "uncertain"}]
    assert bc.diff_briefs(None, new) == {"first": True}
