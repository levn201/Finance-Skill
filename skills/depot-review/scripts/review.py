# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Depot Review support. Prints one JSON object.

    uv run --script review.py dossier          # facts for every Position and Watchlist entry, plus reuse hints
    uv run --script review.py save < review.json   # validate, rank, store in the Journal, diff to the last review

review.json: {"summary": "...", "items": [{"symbol": "SAP.DE", "in": "depot", "view": "hold",
              "confidence": "medium", "reason": "...", "reused": false}, ...], "report_markdown": "..."}
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent
for sub in ("depot-review", "market-data", "assess", "depot", "thesis"):
    sys.path.insert(0, str(SKILLS / sub / "scripts"))

import core as md  # noqa: E402
import depot_core  # noqa: E402
import journal  # noqa: E402
import providers  # noqa: E402
import review_core as rc  # noqa: E402

SUBJECT = "DEPOT"


def _read(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def expected_symbols(depot: dict[str, Any]) -> dict[str, str]:
    out = {p["symbol"]: "depot" for p in depot["positions"]}
    out.update({w["symbol"]: "watchlist" for w in depot["watchlist"]})
    return out


def dossier_item(symbol: str, where: str, root: Path, theses: dict, today: date) -> dict[str, Any]:
    item: dict[str, Any] = {"symbol": symbol, "in": where, "warnings": []}
    try:
        info = providers.yahoo_info(symbol)
        quote = md.normalize_quote(info)
        fundamentals = md.normalize_fundamentals(info)
        rows = providers.yahoo_history(symbol, "1y")
        history = md.summarize_history(rows)
        catalysts, cat_warnings = md.normalize_catalysts(providers.yahoo_calendar(symbol), info, today,
                                                         dated_earnings=providers.yahoo_earnings_dates(symbol))
    except Exception as exc:
        item["warnings"].append(f"data lookup failed ({exc.__class__.__name__}); assess this one by web search")
        return item

    item.update(
        name=quote["name"], type=quote["type"], quote=quote,
        key_figures={"pe_trailing": fundamentals["valuation"]["pe_trailing"],
                     "pe_forward": fundamentals["valuation"]["pe_forward"],
                     "revenue_growth_pct": fundamentals["growth"]["revenue_growth_pct"],
                     "operating_margin_pct": fundamentals["profitability"]["operating_margin_pct"],
                     "dividend_yield_pct": fundamentals["dividend"]["yield_pct"],
                     "analyst_target_mean": fundamentals["analysts"]["target_mean"]},
        history={k: history.get(k) for k in ("return_1m_pct", "return_3m_pct", "return_1y_pct",
                                             "volatility_annualized_pct", "max_drawdown_pct", "above_sma200")},
        next_events=[e for e in catalysts["events"] if e["status"] == "upcoming"],
    )
    item["warnings"] += [w for w in cat_warnings if "AGM" not in w]

    thesis = theses.get(symbol)
    item["thesis"] = None if not thesis or thesis["status"] != "active" else {
        "statement": thesis["statement"], "verdict": thesis["verdict"], "last_checked_at": thesis["last_checked_at"]}

    entries = journal.load_entries(root, "assessment", symbol)
    last = entries[-1] if entries else None
    past_earnings = [e["date"] for e in catalysts["events"] if e["type"] == "earnings"]
    price_then = rc.close_on(rows, last["created_at"][:10]) if last else None
    item["last_assessment"] = None if not last else {
        "created_at": last["created_at"], "view": last["data"]["view"],
        "confidence": last["data"]["confidence"], "summary": last["data"]["outlooks"]}
    item["reuse"] = rc.reuse_decision(last, today, quote["price"], price_then, past_earnings)
    return item


def cmd_dossier(root: Path) -> dict[str, Any]:
    depot = _read(root / "depot.json", depot_core.empty_depot())
    theses = _read(root / "theses.json", {"theses": {}})["theses"]
    expected = expected_symbols(depot)
    today = date.today()
    retrieved = md.now_iso()
    with ThreadPoolExecutor(max_workers=6) as pool:
        items = list(pool.map(lambda kv: dossier_item(kv[0], kv[1], root, theses, today), expected.items()))

    quotes = {i["symbol"]: i.get("quote") or {} for i in items if i["in"] == "depot"}
    fx: dict[str, float] = {}
    currencies = {depot_core.normalize_price(1, q["currency"])[1] for q in quotes.values() if q.get("currency")}
    currencies |= {p["entry_currency"] for p in depot["positions"]}
    for cur in sorted(currencies - {depot["base_currency"]}):
        try:
            rate = md.normalize_quote(providers.yahoo_info(f"{cur}{depot['base_currency']}=X"))["price"]
            if rate:
                fx[cur] = rate
        except Exception:
            pass
    valuation, val_warnings = depot_core.value_depot(depot, quotes, fx) if depot["positions"] else (None, [])

    last_review = (journal.load_entries(root, "depot-review", SUBJECT) or [None])[-1]
    return {
        "as_of": today.isoformat(),
        "items": items,
        "valuation": valuation,
        "valuation_warnings": val_warnings,
        "fx_rates": fx,
        "last_review_at": last_review["created_at"] if last_review else None,
        "sources": [md.source(md.YAHOO, "https://finance.yahoo.com", retrieved)],
        "hints": [] if expected else ["Depot and Watchlist are empty; tell the depot skill what you hold and watch."],
    }


def cmd_save(root: Path, stdin: str) -> dict[str, Any]:
    payload = json.loads(stdin)
    depot = _read(root / "depot.json", depot_core.empty_depot())
    data = {"summary": payload.get("summary"), "items": payload.get("items")}
    for item in data["items"] or []:
        item["symbol"] = str(item.get("symbol", "")).upper()
    rc.validate_review(data, expected_symbols(depot))
    data["items"] = rc.rank(data["items"])
    previous = (journal.load_entries(root, "depot-review", SUBJECT) or [None])[-1]
    saved, _ = journal.save_entry(root, "depot-review",
                                  {"subject": SUBJECT, "data": data, "report_markdown": payload.get("report_markdown")})
    return {"saved": saved["path"], "ranked": data["items"],
            "diff": rc.diff_reviews(previous["data"] if previous else None, data)}


def main() -> int:
    parser = argparse.ArgumentParser(prog="review.py")
    parser.add_argument("command", choices=("dossier", "save"))
    args = parser.parse_args()
    root = md.data_dir()
    result: dict[str, Any] = {"command": args.command, "ok": True, "error": None}
    try:
        result.update(cmd_dossier(root) if args.command == "dossier" else cmd_save(root, sys.stdin.read()))
    except (rc.ReviewError, journal.JournalError, json.JSONDecodeError) as exc:
        result.update(ok=False, error=str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
