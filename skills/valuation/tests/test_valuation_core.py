import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import valuation_core as vc  # noqa: E402


def test_fcf_history_and_base():
    rows = [{"year": "2023-12-31", "fcf": 5.0, "sbc": 1}, {"year": "2025-12-31", "fcf": 9.0, "sbc": 1},
            {"year": "2024-12-31", "fcf": 4.0, "sbc": 1}, {"year": "2021-12-31", "fcf": None, "sbc": None}]
    h = vc.fcf_history(rows)
    assert [r["year"] for r in h] == ["2025-12-31", "2024-12-31", "2023-12-31"]
    assert vc.base_fcf(h, "latest") == 9.0 and vc.base_fcf(h, "avg3") == 6.0
    assert vc.base_fcf([], "avg3") is None
    with pytest.raises(vc.ValuationError):
        vc.base_fcf(h, "median")


def test_start_growth_prefers_ltg_and_clamps():
    assert vc.start_growth({"LTG": 0.09, "+1y": 0.18}, {})[:2] == (0.09, "analyst long-term growth (LTG)")
    g, label, notes = vc.start_growth({"LTG": None, "+1y": 0.35}, {})
    assert g == vc.GROWTH_CAP and "+1y" in label and "clamped" in notes[0]
    assert vc.start_growth({}, {"earningsGrowth": 0.05})[0] == 0.05
    assert vc.start_growth({}, {})[0] is None


def test_discount_rate_capm_and_beta_clamp():
    rate, capm, notes = vc.discount_rate(0.03, 1.2)
    assert rate == pytest.approx(0.09) and not notes
    rate, capm, notes = vc.discount_rate(0.03, 0.4)
    assert capm["beta_used"] == 0.8 and rate == pytest.approx(0.07) and notes
    assert vc.discount_rate(0.03, None)[1]["beta_used"] == 1.0


def test_growth_path_fades_to_terminal():
    path = vc.growth_path(0.12, 0.02)
    assert path[:5] == [0.12] * 5 and path[-1] == pytest.approx(0.02) and len(path) == 10
    assert all(a >= b for a, b in zip(path, path[1:]))


def test_dcf_matches_closed_form_for_flat_growth():
    # growth == terminal everywhere -> a growing perpetuity: FCF x (1+g) / (r-g)
    v = vc.dcf_value(100.0, 0.02, 0.02, 0.08)["equity_value"]
    assert v == pytest.approx(100 * 1.02 / 0.06)
    with pytest.raises(vc.ValuationError):
        vc.dcf_value(100.0, 0.05, 0.03, 0.03)


def test_range_sensitivity_drivers_and_reverse_dcf():
    args = (100.0, 0.08, 0.02, 0.09, 10.0)
    rng = vc.value_range(*args)
    assert rng["low"] < rng["base"] < rng["high"]
    sens = vc.sensitivity(*args)
    assert sens["values"][2][1] == rng["base"]          # centre cell is the base case
    assert sens["values"][0][1] > sens["values"][-1][1]  # higher discount rate, lower value
    d = vc.drivers(*args)
    assert [x["swing_pct"] for x in d] == sorted((x["swing_pct"] for x in d), reverse=True)
    assert next(x for x in d if x["assumption"] == "starting free cash flow")["swing_pct"] == 40.0
    # pricing at the base value implies the base growth back
    assert vc.implied_growth(rng["base"], 100.0, 0.02, 0.09, 10.0) == pytest.approx(0.08, abs=1e-3)
    assert vc.implied_growth(1e9, 100.0, 0.02, 0.09, 10.0) is None
    # currency factor scales linearly
    assert vc.value_range(*args, fx=2.0)["base"] == pytest.approx(rng["base"] * 2, abs=0.02)


def test_dcf_applicable():
    assert vc.dcf_applicable({"sector": "Technology"}, 10.0, 5.0) is None
    assert "Banks" in vc.dcf_applicable({"sector": "Financial Services"}, 10.0, 5.0)
    assert "ETF" in vc.dcf_applicable({"quoteType": "ETF"}, 10.0, 5.0)
    assert "negative" in vc.dcf_applicable({}, -1.0, 5.0)
    assert vc.dcf_applicable({}, None, 5.0) and vc.dcf_applicable({}, 10.0, None)


def test_compare_peers():
    target = {"sector": "Technology", "trailingPE": 30, "forwardPE": 25, "enterpriseToEbitda": 20,
              "enterpriseToRevenue": 6, "priceToBook": 5}
    peers = {"A": {"trailingPE": 20, "forwardPE": 18, "enterpriseToEbitda": 15, "enterpriseToRevenue": 4, "priceToBook": 4},
             "B": {"trailingPE": -12, "forwardPE": 22, "enterpriseToEbitda": 25, "enterpriseToRevenue": 8, "priceToBook": None},
             "C": {"trailingPE": 40, "forwardPE": 30, "enterpriseToEbitda": None, "enterpriseToRevenue": 6, "priceToBook": 6}}
    out = vc.compare_peers(target, peers, price=150.0)
    pe = next(r for r in out["multiples"] if r["multiple"] == "pe_trailing")
    assert pe["peers_with_data"] == 2 and pe["peer_median"] == 30.0  # negative P/E ignored
    assert pe["premium_pct"] == 0.0 and pe["implied_price"] == 150.0
    fwd = next(r for r in out["multiples"] if r["multiple"] == "pe_forward")
    assert fwd["peer_median"] == 22 and fwd["implied_price"] == 132.0
    assert out["implied_range"]["low"] <= out["implied_range"]["median"] <= out["implied_range"]["high"]
    bank = vc.compare_peers({"sector": "Financial Services", "priceToBook": 1.0, "returnOnEquity": 0.075},
                            {"X": {"priceToBook": 1.2, "returnOnEquity": 0.12}, "Y": {"priceToBook": 0.9}}, 10.0)
    assert [r["multiple"] for r in bank["multiples"]] == list(vc.FINANCIAL_MULTIPLES)
    assert bank["return_on_equity"] == {"target_pct": 7.5, "peer_median_pct": 12.0, "peers_pct": {"X": 12.0, "Y": None}}
    assert out["return_on_equity"] is None
    assert vc.compare_peers(target, {}, 150.0)["implied_range"] is None
