# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Earnings facts for one Instrument: next date, consensus, revisions, track record and price reactions.

    uv run --script earnings.py SAP.DE
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
for sub in ("earnings", "market-data"):
    sys.path.insert(0, str(HERE.parent.parent / sub / "scripts"))

import core as md  # noqa: E402
import earnings_core as ec  # noqa: E402
import providers  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"ok": False, "error": "usage: earnings.py <symbol or ISIN>"}))
        return 1
    ident = sys.argv[1].strip()
    try:
        symbol = providers.yahoo_symbol(ident.upper()) if md.is_isin(ident) else ident
        today = date.today()
        retrieved = md.now_iso()
        rows = providers.yahoo_earnings_dates(symbol, limit=16)
        reported, upcoming = ec.split_dates(rows, today)
        closes = providers.yahoo_history(symbol, "5y")
        info = providers.yahoo_info(symbol)
        result = {
            "ok": True, "error": None, "symbol": symbol,
            "name": info.get("longName") or info.get("shortName"),
            "mode": ec.default_mode(reported, today),
            "next": upcoming[0] if upcoming else None,
            "next_is_estimate": bool(upcoming),
            "consensus": ec.consensus(providers.yahoo_estimates(symbol)),
            "track_record": ec.track_record(reported, closes),
            "last_reported": reported[0] if reported else None,
            "quote": md.normalize_quote(info),
            "sources": [md.source(md.YAHOO, md.yahoo_url(symbol) + "/analysis", retrieved),
                        md.source(md.YAHOO, md.yahoo_url(symbol) + "/history", retrieved)],
            "warnings": [],
        }
        if not rows:
            result["warnings"].append("No earnings history from the source; use the company's IR page and web search.")
        if upcoming:
            result["warnings"].append("Yahoo's next earnings date is not confirmed by the company; check the IR calendar.")
    except Exception as exc:
        result = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}",
                  "hints": ["Data source unreachable: use web search for estimates and results (Lite Mode)."]}
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
