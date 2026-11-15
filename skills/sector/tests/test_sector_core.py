import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sector_core as sc  # noqa: E402


def test_sector_etfs_by_industry():
    assert sc.sector_etfs("Technology", "Software - Application") == {"us": "XLK", "europe": "EXV3.DE"}
    assert sc.sector_etfs("Financial Services", "Banks - Regional")["europe"] == "EXV1.DE"
    assert sc.sector_etfs("Financial Services", "Insurance - Diversified")["europe"] == "EXH5.DE"
    assert sc.sector_etfs("Financial Services", "Asset Management")["europe"] == "EXH2.DE"
    assert sc.sector_etfs("Consumer Cyclical", "Auto Manufacturers")["europe"] == "EXV5.DE"
    assert sc.sector_etfs("Basic Materials", "Specialty Chemicals")["europe"] == "EXV7.DE"
    assert sc.sector_etfs(None, None) == {"us": None, "europe": None}
    # every mapped Europe ETF is a known one, and every Yahoo sector has both
    for sector in sc.US_SECTOR_ETFS:
        assert sc.sector_etfs(sector, "")["europe"] in sc.EUROPE_SECTOR_ETFS


def test_relative_performance_sorted_by_3m_excess():
    summaries = {"SPY": {"return_1m_pct": 1.0, "return_3m_pct": 2.0, "return_1y_pct": 10.0},
                 "XLK": {"return_1m_pct": 3.0, "return_3m_pct": 8.0, "return_1y_pct": 20.0, "above_sma200": True},
                 "XLU": {"return_1m_pct": -1.0, "return_3m_pct": -2.0, "return_1y_pct": None},
                 "XLE": {}, "XLB": {"return_3m_pct": None}}
    rows = sc.relative_performance(summaries, {"XLK": "Technology"}, "SPY")
    assert [r["symbol"] for r in rows] == ["XLK", "XLU", "XLB"]  # empty XLE dropped, unknown 3m last
    assert rows[0]["name"] == "Technology" and rows[0]["vs_market_3m_pts"] == 6.0
    assert rows[1]["vs_market_1y_pts"] is None


def _fund(sector, growth, op_margin, de, pe):
    return {"sector": sector, "growth": {"revenue_growth_pct": growth, "earnings_growth_pct": None},
            "profitability": {"gross_margin_pct": None, "operating_margin_pct": op_margin, "profit_margin_pct": None,
                              "return_on_equity_pct": None},
            "balance_sheet": {"debt_to_equity": de}, "valuation": {"pe_forward": pe, "ev_to_ebitda": None},
            "dividend": {"yield_pct": None}}


def test_compare_ranks_shares_strengths():
    funds = {"T": _fund("Technology", 20, 30, 10, 30), "A": _fund("Technology", 10, 20, 50, 20),
             "B": _fund("Technology", 5, 25, 80, 15), "C": _fund("Technology", 15, None, 20, 25)}
    out = sc.compare("T", funds, {"T": 100.0, "A": 300.0, "B": None, "C": 100.0}, {"T": 5.0, "A": 1.0, "B": 2.0, "C": None})
    by = {r["metric"]: r for r in out["summary"]}
    assert by["revenue_growth_pct"]["rank"] == 1 and by["revenue_growth_pct"]["of"] == 4
    assert by["debt_to_equity"]["rank"] == 1          # lowest leverage is best
    assert by["pe_forward"]["rank"] == 4              # most expensive is worst
    assert by["operating_margin_pct"]["of"] == 3 and by["operating_margin_pct"]["median"] == 25
    assert by["return_1y_pct"]["rank"] == 1
    assert "revenue_growth_pct" in out["strengths"] and "pe_forward" in out["weaknesses"]
    assert out["table"]["T"]["revenue_share_pct"] == 20.0 and out["table"]["B"]["revenue_share_pct"] is None
    assert out["revenue_share_note"]


def test_compare_skips_bank_metrics():
    funds = {"BK": _fund("Financial Services", 5, 40, 300, 9), "X": _fund("Financial Services", 3, 35, 250, 8)}
    keys = {r["metric"] for r in sc.compare("BK", funds, {}, {})["summary"]}
    assert "debt_to_equity" not in keys and "operating_margin_pct" not in keys and "pe_forward" in keys
