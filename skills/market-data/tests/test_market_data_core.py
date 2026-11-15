from datetime import date, timedelta

import pytest

import core

TODAY = date(2026, 11, 15)  # the day the Yahoo fixtures were recorded


# --- configuration -----------------------------------------------------------------------------


def test_data_dir_defaults_to_home_and_can_be_overridden(tmp_path):
    assert core.data_dir({}).name == ".financial-support"
    assert core.data_dir({"FINANCIAL_SUPPORT_HOME": str(tmp_path)}) == tmp_path


def test_parse_env_file_handles_comments_quotes_and_export():
    text = "# keys\nFINNHUB_API_KEY='abc'\nexport SEC_USER_AGENT=\"Jane Doe jane@example.com\"\n\nBROKEN\n"
    assert core.parse_env_file(text) == {"FINNHUB_API_KEY": "abc", "SEC_USER_AGENT": "Jane Doe jane@example.com"}


def test_environment_wins_over_env_file(tmp_path):
    (tmp_path / ".env").write_text("FINNHUB_API_KEY=from-file\n")
    env = {"FINANCIAL_SUPPORT_HOME": str(tmp_path)}
    assert core.get_setting("FINNHUB_API_KEY", env) == "from-file"
    assert core.get_setting("FINNHUB_API_KEY", {**env, "FINNHUB_API_KEY": "from-env"}) == "from-env"
    assert core.get_setting("MISSING", env) is None


def test_is_isin():
    assert core.is_isin("DE0007164600")
    assert core.is_isin("ie00b4l5y983")
    assert not core.is_isin("SAP.DE")
    assert not core.is_isin("DE000716460")


def test_envelope_shape():
    env = core.envelope("quote", "SAP.DE", {"price": 1}, [core.source("X", "https://x", "t")])
    assert env["ok"] and env["error"] is None and env["warnings"] == [] and env["sources"][0]["name"] == "X"
    assert not core.envelope("quote", "SAP.DE", None, [], error="boom")["ok"]


# --- quote and fundamentals --------------------------------------------------------------------


def test_quote_sap(fixture):
    q = core.normalize_quote(fixture("yahoo_sap_de.json")["info"])
    assert q["symbol"] == "SAP.DE" and q["currency"] == "EUR" and q["type"] == "EQUITY"
    assert q["price"] > 0 and q["fifty_two_week_low"] <= q["price"] <= q["fifty_two_week_high"]


def test_fundamentals_converts_fractions_to_percent(fixture):
    info = fixture("yahoo_sap_de.json")["info"]
    f = core.normalize_fundamentals(info)
    assert f["profitability"]["gross_margin_pct"] == round(info["grossMargins"] * 100, 2)
    assert f["dividend"]["payout_ratio_pct"] == round(info["payoutRatio"] * 100, 2)
    # yfinance already delivers dividendYield in percent: must not be multiplied again
    assert f["dividend"]["yield_pct"] == round(info["dividendYield"], 2)
    assert f["dividend"]["yield_pct"] < 20
    assert "etf" not in f


def test_fundamentals_etf_has_etf_block_and_nulls_not_guesses(fixture):
    f = core.normalize_fundamentals(fixture("yahoo_eunl_de.json")["info"])
    assert f["type"] == "ETF"
    assert f["etf"]["expense_ratio_pct"] == 0.2
    assert f["valuation"]["pe_trailing"] is None


@pytest.mark.parametrize("bad", [None, "n/a", float("nan"), float("inf"), True])
def test_missing_values_become_none(bad):
    assert core.normalize_quote({"regularMarketPrice": bad, "currentPrice": None})["price"] is None


# --- history -----------------------------------------------------------------------------------


def test_history_summary_on_recorded_year(fixture):
    rows = [tuple(r) for r in fixture("yahoo_aapl.json")["history_1y"]]
    h = core.summarize_history(rows)
    assert h["points"] == len(rows)
    assert h["return_1y_pct"] is not None  # a 1y download must yield a 1y return
    assert h["return_1y_pct"] == round((rows[-1][1] / rows[0][1] - 1) * 100, 2)
    assert h["max_drawdown_pct"] <= 0 and h["volatility_annualized_pct"] > 0
    assert h["period_low"] <= h["last_close"] <= h["period_high"]
    assert h["sma200"] is not None and h["above_sma200"] == (h["last_close"] > h["sma200"])


def test_history_returns_none_when_too_short():
    start = date(2026, 9, 1)
    rows = [((start + timedelta(days=i)).isoformat(), 100.0 + i) for i in range(60)]
    h = core.summarize_history(rows)
    assert h["return_1m_pct"] is not None
    assert h["return_6m_pct"] is None and h["return_1y_pct"] is None
    assert h["sma200"] is None and h["above_sma200"] is None


def test_history_drawdown_and_insufficient_data():
    rows = [("2026-01-01", 100.0), ("2026-01-02", 50.0), ("2026-01-03", 75.0)]
    assert core.summarize_history(rows)["max_drawdown_pct"] == -50.0
    assert core.summarize_history([("2026-01-01", 1.0)])["insufficient_data"]


# --- catalysts ---------------------------------------------------------------------------------


def test_catalysts_never_presents_past_earnings_as_upcoming(fixture):
    sap = fixture("yahoo_sap_de.json")  # Yahoo's latest earnings date (2026-10-21) has passed
    data, warnings = core.normalize_catalysts(sap["calendar"], sap["info"], TODAY)
    earnings = [e for e in data["events"] if e["type"] == "earnings"]
    assert earnings and all(e["status"] == "past" for e in earnings)
    assert any("No confirmed upcoming earnings date" in w for w in warnings)
    assert any("AGM" in w for w in warnings)


def test_catalysts_upcoming_earnings_from_yahoo(fixture):
    aapl = fixture("yahoo_aapl.json")
    data, _ = core.normalize_catalysts(aapl["calendar"], aapl["info"], TODAY)
    earnings = next(e for e in data["events"] if e["type"] == "earnings")
    assert earnings["status"] == "upcoming" and earnings["date"] >= TODAY.isoformat()
    assert earnings["source"] == core.YAHOO
    assert isinstance(earnings["estimated"], bool)


def test_catalysts_prefers_finnhub_when_available(fixture):
    aapl = fixture("yahoo_aapl.json")
    finnhub = fixture("finnhub_aapl_earnings.json")["earningsCalendar"]
    data, _ = core.normalize_catalysts(aapl["calendar"], aapl["info"], TODAY, finnhub)
    earnings = next(e for e in data["events"] if e["type"] == "earnings")
    assert earnings == {
        "type": "earnings",
        "date": "2027-01-29",
        "status": "upcoming",
        "estimated": False,
        "time_of_day": "after market close",
        "eps_estimate": 2.93,
        "revenue_estimate": 157000000000.0,
        "fiscal_period": "Q1 2027",
        "source": core.FINNHUB,
    }


def test_catalysts_fall_back_to_yahoo_earnings_list_as_estimate(fixture):
    sap = fixture("yahoo_sap_de.json")  # calendar only knows the past date 2026-10-21
    listed = [{"date": "2027-01-28", "eps_estimate": 1.98, "eps_reported": None},
              {"date": "2026-10-20", "eps_estimate": 1.83, "eps_reported": 1.89}]
    data, warnings = core.normalize_catalysts(sap["calendar"], sap["info"], TODAY, None, listed)
    earnings = next(e for e in data["events"] if e["type"] == "earnings")
    assert earnings["date"] == "2027-01-28" and earnings["status"] == "upcoming" and earnings["estimated"] is True
    assert any("treat it as an estimate" in w for w in warnings)
    assert not any("No confirmed upcoming" in w for w in warnings)


def test_catalysts_calendar_beats_earnings_list(fixture):
    aapl = fixture("yahoo_aapl.json")
    listed = [{"date": "2027-02-15", "eps_estimate": 3.0, "eps_reported": None}]
    data, _ = core.normalize_catalysts(aapl["calendar"], aapl["info"], TODAY, None, listed)
    assert next(e for e in data["events"] if e["type"] == "earnings")["date"] != "2027-02-15"


def test_catalysts_without_any_data():
    data, warnings = core.normalize_catalysts({}, {}, TODAY)
    assert data == {"events": []}
    assert any("No earnings date" in w for w in warnings)


# --- EDGAR -------------------------------------------------------------------------------------


def test_find_cik(fixture):
    tickers = fixture("edgar_company_tickers.json")
    assert core.find_cik(tickers, "aapl") == "0000320193"
    assert core.find_cik(tickers, "SAP.DE") is None


def test_filings_keep_relevant_forms_and_build_urls(fixture):
    filings = core.normalize_filings(fixture("edgar_aapl_submissions.json"))
    assert [f["form"] for f in filings] == ["10-K", "8-K", "10-Q"]  # Form 4 dropped
    assert filings[0]["url"] == (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019326000101/aapl-20260926.htm"
    )
    assert core.normalize_filings(fixture("edgar_aapl_submissions.json"), limit=1)[0]["form"] == "10-K"
