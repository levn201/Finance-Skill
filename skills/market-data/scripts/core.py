"""Pure logic for market-data: configuration, the result envelope, and normalising raw provider data.

Nothing in here does network I/O, so all of it is tested against recorded provider responses.
"""

from __future__ import annotations

import math
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DATA_DIR_ENV = "FINANCIAL_SUPPORT_HOME"
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

YAHOO = "Yahoo Finance (via yfinance)"
EDGAR = "SEC EDGAR"
FINNHUB = "Finnhub"

SETUP_HINT_FINNHUB = "For more reliable catalyst dates, add a free Finnhub API key by running the `setup` skill."
SETUP_HINT_SEC = (
    "SEC EDGAR requires a contact in every request. Run the `setup` skill to set SEC_USER_AGENT "
    "(e.g. 'Your Name your@email.com'), or use web search for filings."
)
ETF_DATA_WARNING = (
    "Yahoo has only sparse data for many European ETFs. For holdings, TER, fund size and distribution "
    "policy, check the issuer's factsheet or justETF."
)


# --- configuration -----------------------------------------------------------------------------


def data_dir(environ: dict[str, str] | None = None) -> Path:
    """Where the investor's data lives (ADR 0004): ~/.financial-support/ unless overridden."""
    env = os.environ if environ is None else environ
    override = env.get(DATA_DIR_ENV)
    return Path(override).expanduser() if override else Path.home() / ".financial-support"


def parse_env_file(text: str) -> dict[str, str]:
    """Parse a minimal KEY=VALUE .env file. Blank lines and # comments are ignored."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def get_setting(name: str, environ: dict[str, str] | None = None) -> str | None:
    """A setting such as FINNHUB_API_KEY. The environment wins over <data dir>/.env."""
    env = os.environ if environ is None else environ
    if env.get(name):
        return env[name]
    env_file = data_dir(env) / ".env"
    if env_file.is_file():
        return parse_env_file(env_file.read_text(encoding="utf-8")).get(name) or None
    return None


# --- envelope ----------------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def source(name: str, url: str, retrieved_at: str) -> dict[str, str]:
    return {"name": name, "url": url, "retrieved_at": retrieved_at}


def envelope(
    command: str,
    instrument: str | None,
    data: Any,
    sources: list[dict[str, str]],
    warnings: list[str] | None = None,
    hints: list[str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Every command returns this shape so skills can always cite sources and surface warnings."""
    return {
        "command": command,
        "instrument": instrument,
        "ok": error is None,
        "error": error,
        "data": data,
        "sources": sources,
        "warnings": warnings or [],
        "hints": hints or [],
    }


def is_isin(identifier: str) -> bool:
    return bool(ISIN_RE.match(identifier.strip().upper()))


def yahoo_url(symbol: str) -> str:
    return f"https://finance.yahoo.com/quote/{symbol}"


# --- helpers -----------------------------------------------------------------------------------


def _num(value: Any) -> float | None:
    """A finite float, or None for missing/NaN/non-numeric values (never guess)."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _pct(fraction: Any) -> float | None:
    f = _num(fraction)
    return None if f is None else round(f * 100, 2)


def _round(value: Any, digits: int = 2) -> float | None:
    f = _num(value)
    return None if f is None else round(f, digits)


def _epoch_to_date(value: Any) -> str | None:
    f = _num(value)
    if f is None:
        return None
    return datetime.fromtimestamp(f, tz=timezone.utc).date().isoformat()


def _to_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    if _num(value) is not None:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).date()
    return None


# --- normalisation: Yahoo ----------------------------------------------------------------------


def normalize_quote(info: dict[str, Any]) -> dict[str, Any]:
    price = _num(info.get("regularMarketPrice")) or _num(info.get("currentPrice"))
    return {
        "symbol": info.get("symbol"),
        "name": info.get("longName") or info.get("shortName"),
        "type": info.get("quoteType"),
        "exchange": info.get("fullExchangeName") or info.get("exchange"),
        "currency": info.get("currency"),
        "price": _round(price, 4),
        "change_pct": _round(info.get("regularMarketChangePercent")),
        "previous_close": _round(info.get("regularMarketPreviousClose") or info.get("previousClose"), 4),
        "fifty_two_week_low": _round(info.get("fiftyTwoWeekLow"), 4),
        "fifty_two_week_high": _round(info.get("fiftyTwoWeekHigh"), 4),
        "market_cap": _num(info.get("marketCap")),
        "price_time": _epoch_to_date(info.get("regularMarketTime")),
        "delayed_by_minutes": _num(info.get("exchangeDataDelayedBy")),
    }


def normalize_fundamentals(info: dict[str, Any]) -> dict[str, Any]:
    """Key figures. Ratios Yahoo delivers as fractions are converted to percent (suffix _pct).

    yfinance >= 0.2.54 already delivers `dividendYield` in percent; `payoutRatio` and margins are fractions.
    """
    data: dict[str, Any] = {
        "symbol": info.get("symbol"),
        "type": info.get("quoteType"),
        "currency": info.get("financialCurrency") or info.get("currency"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "valuation": {
            "pe_trailing": _round(info.get("trailingPE")),
            "pe_forward": _round(info.get("forwardPE")),
            "peg": _round(info.get("trailingPegRatio") or info.get("pegRatio")),
            "price_to_book": _round(info.get("priceToBook")),
            "price_to_sales": _round(info.get("priceToSalesTrailing12Months")),
            "ev_to_ebitda": _round(info.get("enterpriseToEbitda")),
        },
        "growth": {
            "revenue_growth_pct": _pct(info.get("revenueGrowth")),
            "earnings_growth_pct": _pct(info.get("earningsGrowth")),
        },
        "profitability": {
            "gross_margin_pct": _pct(info.get("grossMargins")),
            "operating_margin_pct": _pct(info.get("operatingMargins")),
            "profit_margin_pct": _pct(info.get("profitMargins")),
            "return_on_equity_pct": _pct(info.get("returnOnEquity")),
        },
        "balance_sheet": {
            "debt_to_equity": _round(info.get("debtToEquity")),
            "current_ratio": _round(info.get("currentRatio")),
            "total_cash": _num(info.get("totalCash")),
            "total_debt": _num(info.get("totalDebt")),
            "free_cashflow": _num(info.get("freeCashflow")),
        },
        "dividend": {
            "yield_pct": _round(info.get("dividendYield")),
            "rate": _round(info.get("dividendRate"), 4),
            "payout_ratio_pct": _pct(info.get("payoutRatio")),
            "five_year_avg_yield_pct": _round(info.get("fiveYearAvgDividendYield")),
        },
        "analysts": {
            "recommendation": info.get("recommendationKey"),
            "count": _num(info.get("numberOfAnalystOpinions")),
            "target_mean": _round(info.get("targetMeanPrice"), 4),
            "target_low": _round(info.get("targetLowPrice"), 4),
            "target_high": _round(info.get("targetHighPrice"), 4),
        },
        "most_recent_quarter": _epoch_to_date(info.get("mostRecentQuarter")),
    }
    if info.get("quoteType") == "ETF":
        data["etf"] = {
            "expense_ratio_pct": _round(info.get("netExpenseRatio")),
            "total_assets": _num(info.get("totalAssets")),
            "ytd_return_pct": _round(info.get("ytdReturn")),
            "three_year_avg_return_pct": _pct(info.get("threeYearAverageReturn")),
            "fund_family": info.get("fundFamily"),
            "category": info.get("category"),
        }
    return data


def summarize_history(rows: list[tuple[str, float]]) -> dict[str, Any]:
    """Summary statistics of daily closes [(iso_date, close), ...] in chronological order.

    Returns are simple returns in percent over 1/3/6/12 calendar months: the last close against the
    last close on or before the start date. A return is None when the history doesn't reach back far
    enough, with a tolerance of one week for holidays and the gap at the start of a download.
    Volatility is the annualised standard deviation of daily log returns, in percent.
    """
    closes = [(d, c) for d, c in rows if _num(c) is not None and c > 0]
    if len(closes) < 2:
        return {"points": len(closes), "insufficient_data": True}

    values = [c for _, c in closes]
    dates = [date.fromisoformat(d[:10]) for d, _ in closes]
    last = values[-1]

    def ret(calendar_days: int) -> float | None:
        start = dates[-1] - timedelta(days=calendar_days)
        if dates[0] > start + timedelta(days=7):
            return None
        base = next(v for d, v in zip(reversed(dates), reversed(values)) if d <= max(start, dates[0]))
        return round((last / base - 1) * 100, 2)

    def sma(days: int) -> float | None:
        if len(values) < days:
            return None
        return round(sum(values[-days:]) / days, 4)

    log_returns = [math.log(b / a) for a, b in zip(values, values[1:])]
    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / max(len(log_returns) - 1, 1)
    volatility = round(math.sqrt(variance) * math.sqrt(252) * 100, 2)

    peak = values[0]
    max_drawdown = 0.0
    for v in values:
        peak = max(peak, v)
        max_drawdown = min(max_drawdown, v / peak - 1)

    high, low = max(values), min(values)
    sma50, sma200 = sma(50), sma(200)
    return {
        "points": len(values),
        "from": closes[0][0],
        "to": closes[-1][0],
        "last_close": round(last, 4),
        "return_1m_pct": ret(30),
        "return_3m_pct": ret(91),
        "return_6m_pct": ret(182),
        "return_1y_pct": ret(365),
        "volatility_annualized_pct": volatility,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "period_high": round(high, 4),
        "period_low": round(low, 4),
        "distance_from_high_pct": round((last / high - 1) * 100, 2),
        "sma50": sma50,
        "sma200": sma200,
        "above_sma50": None if sma50 is None else last > sma50,
        "above_sma200": None if sma200 is None else last > sma200,
    }


def normalize_catalysts(
    calendar: dict[str, Any] | None,
    info: dict[str, Any],
    today: date,
    finnhub_earnings: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Upcoming dated events for one Instrument, plus warnings.

    Each event has a status: "upcoming" or "past". A past date is never presented as the next one.
    Finnhub, when available, takes precedence for the earnings date because Yahoo dates are often
    estimates or stale.
    """
    calendar = calendar or {}
    warnings: list[str] = []
    events: list[dict[str, Any]] = []

    def status(d: date) -> str:
        return "upcoming" if d >= today else "past"

    finnhub_upcoming = [
        e for e in (finnhub_earnings or []) if (_to_date(e.get("date")) or date.min) >= today
    ]
    if finnhub_upcoming:
        nxt = min(finnhub_upcoming, key=lambda e: e["date"])
        events.append({
            "type": "earnings",
            "date": nxt["date"],
            "status": "upcoming",
            "estimated": False,
            "time_of_day": {"bmo": "before market open", "amc": "after market close"}.get(nxt.get("hour") or "", None),
            "eps_estimate": _round(nxt.get("epsEstimate"), 4),
            "revenue_estimate": _num(nxt.get("revenueEstimate")),
            "fiscal_period": f"Q{nxt['quarter']} {nxt['year']}" if nxt.get("quarter") and nxt.get("year") else None,
            "source": FINNHUB,
        })
    else:
        earnings_dates = [d for d in (_to_date(x) for x in (calendar.get("Earnings Date") or [])) if d]
        if not earnings_dates and info.get("earningsTimestampStart"):
            d = _to_date(info.get("earningsTimestampStart"))
            earnings_dates = [d] if d else []
        upcoming = sorted(d for d in earnings_dates if d >= today)
        if upcoming:
            events.append({
                "type": "earnings",
                "date": upcoming[0].isoformat(),
                "status": "upcoming",
                "estimated": bool(info.get("isEarningsDateEstimate")),
                "eps_estimate": _round(calendar.get("Earnings Average"), 4),
                "revenue_estimate": _num(calendar.get("Revenue Average")),
                "source": YAHOO,
            })
        elif earnings_dates:
            last = max(earnings_dates)
            events.append({"type": "earnings", "date": last.isoformat(), "status": "past", "source": YAHOO})
            warnings.append(
                f"No confirmed upcoming earnings date; the latest one the source knows ({last.isoformat()}) "
                "has already passed. Check the company's investor-relations page."
            )
        else:
            warnings.append("No earnings date available from the source.")

    ex_div = _to_date(calendar.get("Ex-Dividend Date")) or _to_date(info.get("exDividendDate"))
    if ex_div:
        events.append({"type": "ex_dividend", "date": ex_div.isoformat(), "status": status(ex_div), "source": YAHOO})
        if ex_div < today:
            warnings.append(f"Next ex-dividend date not yet announced; the last one was {ex_div.isoformat()}.")

    warnings.append("AGM dates are not provided by these data sources; use the company's investor-relations page.")
    return {"events": events}, warnings


# --- normalisation: EDGAR ----------------------------------------------------------------------

EDGAR_FORMS = {"10-K", "10-Q", "8-K", "20-F", "6-K", "DEF 14A"}


def find_cik(ticker_map: dict[str, Any], ticker: str) -> str | None:
    """Look up a CIK in SEC's company_tickers.json structure."""
    wanted = ticker.upper()
    for entry in ticker_map.values():
        if str(entry.get("ticker", "")).upper() == wanted:
            return str(entry["cik_str"]).zfill(10)
    return None


def normalize_filings(submissions: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    cik = str(submissions.get("cik", "")).lstrip("0")
    out = []
    for form, filed, accession, doc, period in zip(
        recent.get("form", []),
        recent.get("filingDate", []),
        recent.get("accessionNumber", []),
        recent.get("primaryDocument", []),
        recent.get("reportDate", []),
    ):
        if form not in EDGAR_FORMS:
            continue
        out.append({
            "form": form,
            "filed": filed,
            "period": period or None,
            "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{doc}",
        })
        if len(out) >= limit:
            break
    return out
