"""Thin network layer: fetches raw data from providers. No interpretation happens here (see core.py)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

TIMEOUT = 20


def _get_json(url: str, headers: dict[str, str] | None = None) -> Any:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


# --- Yahoo (yfinance) --------------------------------------------------------------------------


def _yf():
    import yfinance  # imported lazily so `status` and tests work without it

    return yfinance


def yahoo_symbol(identifier: str) -> str:
    """Ticker as given, or the Yahoo symbol behind an ISIN."""
    return _yf().Ticker(identifier).ticker


def yahoo_info(symbol: str) -> dict[str, Any]:
    return dict(_yf().Ticker(symbol).info or {})


def yahoo_calendar(symbol: str) -> dict[str, Any]:
    try:
        return dict(_yf().Ticker(symbol).calendar or {})
    except Exception:  # yfinance raises for instruments without a calendar (e.g. many ETFs)
        return {}


def yahoo_history(symbol: str, period: str) -> list[tuple[str, float]]:
    frame = _yf().Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
    return [(idx.date().isoformat(), float(close)) for idx, close in frame["Close"].items()]


def yahoo_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    quotes = _yf().Search(query, max_results=limit).quotes
    return [
        {
            "symbol": q.get("symbol"),
            "name": q.get("longname") or q.get("shortname"),
            "type": q.get("quoteType"),
            "exchange": q.get("exchDisp") or q.get("exchange"),
        }
        for q in quotes
    ]


# --- SEC EDGAR ---------------------------------------------------------------------------------


def edgar_ticker_map(user_agent: str) -> dict[str, Any]:
    return _get_json("https://www.sec.gov/files/company_tickers.json", {"User-Agent": user_agent})


def edgar_submissions(cik: str, user_agent: str) -> dict[str, Any]:
    return _get_json(f"https://data.sec.gov/submissions/CIK{cik}.json", {"User-Agent": user_agent})


# --- Finnhub -----------------------------------------------------------------------------------


def finnhub_earnings(symbol: str, api_key: str, date_from: str, date_to: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"symbol": symbol, "from": date_from, "to": date_to})
    payload = _get_json(
        f"https://finnhub.io/api/v1/calendar/earnings?{query}", {"X-Finnhub-Token": api_key}
    )
    return payload.get("earningsCalendar") or []


# --- connectivity ------------------------------------------------------------------------------


def reachable(url: str = "https://query1.finance.yahoo.com", timeout: float = 5) -> bool:
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True  # the host answered, so the network works
    except Exception:
        return False
