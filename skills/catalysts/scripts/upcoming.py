# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Catalyst calendar for the Depot and Watchlist. Prints one JSON object.

    uv run --script upcoming.py [--days 90] [--symbol SAP.DE ...] [--save] < extra_events.json

stdin (optional): a JSON list of events found by web search, each
    {"date": "2026-12-17", "type": "central_bank|agm|macro|earnings|ex_dividend|other",
     "symbol": null, "title": "ECB monetary policy meeting", "source": "ECB", "url": "https://..."}
--save stores the calendar in the Journal (kind "catalysts") and returns what changed since the last saved one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SKILLS / "market-data" / "scripts"))
sys.path.insert(0, str(SKILLS / "assess" / "scripts"))

import catalysts_core as cc  # noqa: E402
import core as md  # noqa: E402
import journal  # noqa: E402
import providers  # noqa: E402

JOURNAL_SUBJECT = "DEPOT"


def load_context(root: Path, symbols: list[str]) -> dict[str, dict[str, Any]]:
    path = root / "depot.json"
    depot = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"positions": [], "watchlist": []}
    context = {p["symbol"]: {"name": p.get("name"), "in": "depot"} for p in depot["positions"]}
    context.update({w["symbol"]: {"name": w.get("name"), "in": "watchlist"} for w in depot["watchlist"]})
    for s in symbols:
        context.setdefault(s.upper(), {"name": None, "in": "other"})
    return context if not symbols else {s.upper(): context[s.upper()] for s in symbols}


def fetch_one(symbol: str, today: date, finnhub_key: str | None) -> tuple[str, dict[str, Any]]:
    try:
        finnhub_rows = None
        if finnhub_key:
            try:
                finnhub_rows = providers.finnhub_earnings(symbol, finnhub_key, today.isoformat(),
                                                          (today + timedelta(days=180)).isoformat())
            except Exception:
                finnhub_rows = None
        data, warnings = md.normalize_catalysts(providers.yahoo_calendar(symbol), providers.yahoo_info(symbol),
                                                today, finnhub_rows, providers.yahoo_earnings_dates(symbol))
        return symbol, {"events": data["events"], "warnings": warnings}
    except Exception as exc:
        return symbol, {"events": [], "warnings": [f"lookup failed ({exc.__class__.__name__})"]}


def run(argv: list[str], stdin: str | None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="upcoming.py")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    root = md.data_dir()
    today = date.today()
    result: dict[str, Any] = {"ok": True, "error": None, "hints": []}
    try:
        extra = cc.validate_extra(json.loads(stdin) if stdin and stdin.strip() else [])
        context = load_context(root, args.symbol)
        if not context:
            result["hints"].append("Depot and Watchlist are empty; tell the depot skill what you hold and watch.")
        key = md.get_setting("FINNHUB_API_KEY")
        if not key:
            result["hints"].append(md.SETUP_HINT_FINNHUB)
        with ThreadPoolExecutor(max_workers=6) as pool:
            per_symbol = dict(pool.map(lambda s: fetch_one(s, today, key), context))
        calendar = cc.build_calendar(per_symbol, context, extra, today, args.days)
        retrieved = md.now_iso()
        calendar["sources"] = [md.source(md.YAHOO, "https://finance.yahoo.com", retrieved)]
        if key:
            calendar["sources"].append(md.source(md.FINNHUB, "https://finnhub.io/docs/api/earnings-calendar", retrieved))
        calendar["sources"] += [{"name": e["source"], "url": e["url"], "retrieved_at": retrieved} for e in extra]
        result["calendar"] = calendar

        if args.save:
            last = journal.load_entries(root, "catalysts", JOURNAL_SUBJECT)
            previous = last[-1]["data"]["events"] if last else None
            saved, _ = journal.save_entry(root, "catalysts", {"subject": JOURNAL_SUBJECT, "data": calendar})
            result["saved"] = saved["path"]
            result["diff"] = cc.diff_calendars(previous, calendar["events"], today)
    except (cc.CatalystError, journal.JournalError, json.JSONDecodeError) as exc:
        result.update(ok=False, error=str(exc))
    return result


def main() -> int:
    try:
        argv, text, path = journal.take_input(sys.argv[1:])
    except journal.JournalError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    stdin = text if text is not None else (None if sys.stdin.isatty() else sys.stdin.read())
    result = run(argv, stdin)
    if result["ok"]:
        journal.consume_input(md.data_dir(), path)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
