# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""market-data CLI. Prints one JSON envelope per call (see core.envelope).

    uv run fetch.py status
    uv run fetch.py resolve "SAP"
    uv run fetch.py quote SAP.DE
    uv run fetch.py fundamentals DE0007164600
    uv run fetch.py history AAPL --period 1y
    uv run fetch.py catalysts SAP.DE
    uv run fetch.py filings AAPL
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core  # noqa: E402
import providers  # noqa: E402


def _symbol(identifier: str) -> str:
    identifier = identifier.strip()
    return providers.yahoo_symbol(identifier.upper()) if core.is_isin(identifier) else identifier


def cmd_status(_: argparse.Namespace) -> dict:
    data_dir = core.data_dir()
    probe = data_dir if data_dir.exists() else data_dir.parent
    network = providers.reachable()
    finnhub = core.get_setting("FINNHUB_API_KEY") is not None
    profile = data_dir / "profile.json"
    data = {
        "data_dir": str(data_dir),
        "inbox": str(data_dir / "inbox"),
        "data_dir_exists": data_dir.exists(),
        "data_dir_writable": os.access(probe, os.W_OK),
        "profile_exists": profile.is_file(),
        "network": network,
        "keys": {"finnhub": finnhub},
        "mode": "full" if network and os.access(probe, os.W_OK) else "lite",
    }
    hints = []
    if not data["profile_exists"]:
        hints.append("No Investor Profile yet. Run the `setup` skill.")
    if not finnhub:
        hints.append(core.SETUP_HINT_FINNHUB)
    return core.envelope("status", None, data, [], hints=hints)


def cmd_resolve(args: argparse.Namespace) -> dict:
    retrieved = core.now_iso()
    if core.is_isin(args.query):
        symbol = providers.yahoo_symbol(args.query.upper())
        results = [{"symbol": symbol, "isin": args.query.upper()}]
    else:
        results = providers.yahoo_search(args.query)
    src = [core.source(core.YAHOO, "https://finance.yahoo.com/lookup", retrieved)]
    warnings = [] if results else [f"No Instrument found for '{args.query}'."]
    return core.envelope("resolve", args.query, {"matches": results}, src, warnings)


def cmd_quote(args: argparse.Namespace) -> dict:
    symbol = _symbol(args.instrument)
    retrieved = core.now_iso()
    data = core.normalize_quote(providers.yahoo_info(symbol))
    warnings = [] if data["price"] is not None else ["No price available from the source."]
    return core.envelope("quote", symbol, data, [core.source(core.YAHOO, core.yahoo_url(symbol), retrieved)], warnings)


def cmd_fundamentals(args: argparse.Namespace) -> dict:
    symbol = _symbol(args.instrument)
    retrieved = core.now_iso()
    data = core.normalize_fundamentals(providers.yahoo_info(symbol))
    url = core.yahoo_url(symbol) + "/key-statistics"
    warnings = [core.ETF_DATA_WARNING] if data["type"] == "ETF" else []
    return core.envelope("fundamentals", symbol, data, [core.source(core.YAHOO, url, retrieved)], warnings)


def cmd_history(args: argparse.Namespace) -> dict:
    symbol = _symbol(args.instrument)
    retrieved = core.now_iso()
    rows = providers.yahoo_history(symbol, args.period)
    data = core.summarize_history(rows)
    if args.raw:
        data["closes"] = rows
    url = core.yahoo_url(symbol) + "/history"
    warnings = ["Not enough price history."] if data.get("insufficient_data") else []
    return core.envelope("history", symbol, data, [core.source(core.YAHOO, url, retrieved)], warnings)


def cmd_catalysts(args: argparse.Namespace) -> dict:
    symbol = _symbol(args.instrument)
    retrieved = core.now_iso()
    today = date.today()
    sources = [core.source(core.YAHOO, core.yahoo_url(symbol), retrieved)]
    hints: list[str] = []
    warnings: list[str] = []

    finnhub_rows = None
    key = core.get_setting("FINNHUB_API_KEY")
    if key:
        try:
            finnhub_rows = providers.finnhub_earnings(
                symbol, key, today.isoformat(), (today + timedelta(days=180)).isoformat()
            )
            sources.append(core.source(core.FINNHUB, "https://finnhub.io/docs/api/earnings-calendar", retrieved))
        except Exception as exc:  # fall back to Yahoo, but say so
            warnings.append(f"Finnhub request failed ({exc.__class__.__name__}); using Yahoo dates only.")
    else:
        hints.append(core.SETUP_HINT_FINNHUB)

    data, more_warnings = core.normalize_catalysts(
        providers.yahoo_calendar(symbol), providers.yahoo_info(symbol), today, finnhub_rows,
        providers.yahoo_earnings_dates(symbol),
    )
    return core.envelope("catalysts", symbol, data, sources, warnings + more_warnings, hints)


def cmd_filings(args: argparse.Namespace) -> dict:
    ticker = args.ticker.upper()
    retrieved = core.now_iso()
    user_agent = core.get_setting("SEC_USER_AGENT")
    if not user_agent:
        return core.envelope(
            "filings", ticker, {"filings": []}, [], ["SEC filings unavailable: SEC_USER_AGENT is not set."],
            [core.SETUP_HINT_SEC],
        )
    cik = core.find_cik(providers.edgar_ticker_map(user_agent), ticker)
    if not cik:
        return core.envelope(
            "filings", ticker, {"filings": []}, [],
            [f"{ticker} is not an SEC registrant. EDGAR only covers US-listed companies; for German/EU "
             "companies use their investor-relations page or the Unternehmensregister."],
        )
    filings = core.normalize_filings(providers.edgar_submissions(cik, user_agent), args.limit)
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
    return core.envelope("filings", ticker, {"cik": cik, "filings": filings}, [core.source(core.EDGAR, url, retrieved)])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fetch.py", description="Fetch market data as JSON.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Check data dir, keys and network; tells you full vs lite mode")
    p = sub.add_parser("resolve", help="Find symbols by name, ticker or ISIN")
    p.add_argument("query")
    for name, func_help in [("quote", "Current price"), ("fundamentals", "Key figures"), ("catalysts", "Upcoming dated events")]:
        p = sub.add_parser(name, help=func_help)
        p.add_argument("instrument", help="Yahoo symbol (e.g. SAP.DE, AAPL) or ISIN")
    p = sub.add_parser("history", help="Price history summary (returns, volatility, drawdown, moving averages)")
    p.add_argument("instrument")
    p.add_argument("--period", default="1y", help="1mo, 3mo, 6mo, 1y, 2y, 5y, max (default 1y)")
    p.add_argument("--raw", action="store_true", help="Also include the daily closes")
    p = sub.add_parser("filings", help="Recent SEC filings (US companies only)")
    p.add_argument("ticker")
    p.add_argument("--limit", type=int, default=10)
    return parser


COMMANDS = {
    "status": cmd_status,
    "resolve": cmd_resolve,
    "quote": cmd_quote,
    "fundamentals": cmd_fundamentals,
    "history": cmd_history,
    "catalysts": cmd_catalysts,
    "filings": cmd_filings,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    instrument = getattr(args, "instrument", None) or getattr(args, "ticker", None) or getattr(args, "query", None)
    try:
        result = COMMANDS[args.command](args)
    except Exception as exc:
        result = core.envelope(
            args.command, instrument, None, [],
            error=f"{exc.__class__.__name__}: {exc}",
            hints=["If this keeps failing, the data source may be unreachable here: switch to Lite Mode."],
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
