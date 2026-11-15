import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import screen_core as sc  # noqa: E402


def test_filter_candidates_keeps_home_companies_once():
    quotes = [{"symbol": "SAP.DE"}, {"symbol": "APC.DE"}, {"symbol": "SAPA.DE"}, {"symbol": "X.DE"}, {"symbol": "OTC1"}]
    infos = {
        "SAP.DE": {"longName": "SAP SE", "country": "Germany", "exchange": "GER"},
        "APC.DE": {"longName": "Apple Inc.", "country": "United States", "exchange": "GER"},
        "SAPA.DE": {"longName": "SAP SE", "country": "Germany", "exchange": "GER"},
        "OTC1": {"longName": "Iberdrola", "country": "Spain", "exchange": "PNK"},
    }
    kept, dropped = sc.filter_candidates(quotes, infos, "Germany")
    assert kept == ["SAP.DE"]
    reasons = {d["symbol"]: d["reason"] for d in dropped}
    assert "United States" in reasons["APC.DE"] and "same company" in reasons["SAPA.DE"]
    assert reasons["OTC1"] == "OTC listing" and "unknown" in reasons["X.DE"]


def test_prefilter_by_reporting_currency_and_otc():
    quotes = [{"symbol": "APC.DE", "financialCurrency": "USD"}, {"symbol": "SAP.DE", "financialCurrency": "EUR"},
              {"symbol": "X.DE"}, {"symbol": "O", "exchange": "PNK", "financialCurrency": "EUR"},
              {"symbol": "SIE.DE", "financialCurrency": "EUR"}]
    assert [q["symbol"] for q in sc.prefilter_quotes(quotes, "EUR", 10)] == ["SAP.DE", "X.DE", "SIE.DE"]
    assert [q["symbol"] for q in sc.prefilter_quotes(quotes, "EUR", 1)] == ["SAP.DE"]
    assert len(sc.prefilter_quotes(quotes, None, 10)) == 4


def test_filter_without_country_keeps_foreign():
    kept, _ = sc.filter_candidates([{"symbol": "APC.DE"}], {"APC.DE": {"longName": "Apple", "country": "United States"}}, None)
    assert kept == ["APC.DE"]


def fundamentals(pe=20, growth=10, margin=20, roe=15, de=50, yld=2.0, payout=50):
    return {"valuation": {"pe_forward": pe, "ev_to_ebitda": 12, "peg": 1.5}, "growth": {"revenue_growth_pct": growth},
            "profitability": {"operating_margin_pct": margin, "return_on_equity_pct": roe},
            "balance_sheet": {"debt_to_equity": de}, "dividend": {"yield_pct": yld, "payout_ratio_pct": payout}}


def test_metrics_from_drops_negative_pe_and_rates_payout():
    m = sc.metrics_from(fundamentals(pe=-5, payout=120), {"return_6m_pct": 5, "return_1y_pct": 10, "above_sma200": True})
    assert m["pe_forward"] is None and m["payout_health"] == 0.0 and m["sma200_trend"] == 100.0
    assert sc.metrics_from(fundamentals(payout=50), {})["payout_health"] == 100.0
    assert sc.metrics_from(fundamentals(yld=None, payout=None), {})["dividend_yield_pct"] == 0.0  # no dividend = 0 %


def test_financials_skip_leverage_and_ev_ebitda():
    bank = {**fundamentals(de=900), "sector": "Financial Services"}
    m = sc.metrics_from(bank, {})
    assert m["debt_to_equity"] is None and m["ev_to_ebitda"] is None and m["pe_forward"] == 20
    assert sc.metrics_from({**fundamentals(de=900), "sector": "Industrials"}, {})["debt_to_equity"] == 900


def test_percentiles_direction_and_ties():
    up = sc._percentiles({"a": 1, "b": 2, "c": 3, "d": None}, True)
    assert up == {"a": 0.0, "b": 50.0, "c": 100.0}
    down = sc._percentiles({"a": 1, "b": 2, "c": 3}, False)
    assert down["a"] == 100.0 and down["c"] == 0.0
    assert sc._percentiles({"a": 5, "b": 5}, True) == {"a": 50.0, "b": 50.0}
    assert sc._percentiles({"a": 5}, True) == {"a": 50.0}


def make(**over):
    base = {"good": sc.metrics_from(fundamentals(pe=12, growth=20, margin=30, roe=25, de=20, yld=3), {"return_6m_pct": 15, "return_1y_pct": 30, "above_sma200": True}),
            "mid": sc.metrics_from(fundamentals(), {"return_6m_pct": 5, "return_1y_pct": 8, "above_sma200": True}),
            "bad": sc.metrics_from(fundamentals(pe=45, growth=-5, margin=5, roe=3, de=200, yld=0, payout=None), {"return_6m_pct": -20, "return_1y_pct": -30, "above_sma200": False})}
    base.update(over)
    return base


def test_score_ranks_and_spreads_thematic_weight_without_theme():
    rows, notes = sc.score(make(), sc.DEFAULT_WEIGHTS)
    assert [r["symbol"] for r in rows] == ["good", "mid", "bad"]
    # spreading the thematic weight on purpose is not a data gap
    assert rows[0]["criteria"]["thematic"] is None and rows[0]["coverage_pct"] == 100
    assert notes and "thematic weight" in notes[0]


def test_theme_fit_can_change_the_ranking():
    weights = {"fundamentals": 10, "valuation": 10, "dividend": 0, "thematic": 80, "technical": 0}
    rows, notes = sc.score(make(), weights, {"good": 0, "mid": 10, "bad": 100})
    assert rows[0]["symbol"] == "bad" and not notes
    assert rows[0]["coverage_pct"] == 100


def test_missing_data_lowers_coverage_not_score():
    m = make(empty={k: None for k in make()["good"]})
    rows, _ = sc.score(m, sc.DEFAULT_WEIGHTS)
    empty = next(r for r in rows if r["symbol"] == "empty")
    assert empty["score"] is None and empty["coverage_pct"] == 0 and empty["rank"] == 4


def test_parse_fit():
    assert sc.parse_fit(["rhm.de=95", "AIR.PA=55.5"]) == {"RHM.DE": 95.0, "AIR.PA": 55.5}
    for bad, message in [(["RHM.DE"], "SYMBOL=0-100"), (["RHM.DE=high"], "must be a number"), (["RHM.DE=120"], "between 0 and 100")]:
        with pytest.raises(sc.ScreenError, match=message):
            sc.parse_fit(bad)


def test_score_validates_weights():
    with pytest.raises(sc.ScreenError, match="exactly"):
        sc.score(make(), {"fundamentals": 100})
    with pytest.raises(sc.ScreenError, match="above 0"):
        sc.score(make(), {"fundamentals": 0, "valuation": 0, "dividend": 0, "thematic": 10, "technical": 0})
