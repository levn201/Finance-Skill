# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Market Brief support. Prints one JSON object.

    uv run --script brief.py data             # market indicators, volatility regime, yield curve, Depot exposure
    uv run --script brief.py save < brief.json   # validate, store in the Journal, diff to the last Market Brief

brief.json: {"regime": "normal", "indicators": <data.indicators>, "themes": [{"title": "...",
  "category": "trade", "direction": "negative", "affects": ["AAPL"], "sources": [{"name": "...", "url": "...",
  "as_of": "2026-11-14"}]}], "depot_impact": "...", "report_markdown": "..."}
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent
for sub in ("market-brief", "market-data", "assess", "depot"):
    sys.path.insert(0, str(SKILLS / sub / "scripts"))

import brief_core as bc  # noqa: E402
import core as md  # noqa: E402
import depot_core  # noqa: E402
import journal  # noqa: E402
import providers  # noqa: E402

SUBJECT = "GLOBAL"


def _indicator(symbol: str) -> tuple[str, dict[str, Any] | None]:
    try:
        return symbol, bc.indicator_summary(providers.yahoo_history(symbol, "1y"))
    except Exception:
        return symbol, None


def _instrument(symbol: str) -> dict[str, Any]:
    try:
        info = providers.yahoo_info(symbol)
    except Exception:
        info = {}
    q = md.normalize_quote(info) if info else {}
    return {"symbol": symbol, "name": q.get("name"), "type": info.get("quoteType"), "sector": info.get("sector"),
            "country": info.get("country"), "currency": depot_core.normalize_price(1, info["currency"])[1] if info.get("currency") else None,
            "quote": q}


def cmd_data(root: Path) -> dict[str, Any]:
    retrieved = md.now_iso()
    with ThreadPoolExecutor(max_workers=8) as pool:
        indicators = dict(pool.map(_indicator, bc.INDICATORS))
    missing = [s for s, v in indicators.items() if v is None]
    vix = (indicators.get("^VIX") or {}).get("last")
    curve = bc.yield_curve((indicators.get("^TNX") or {}).get("last"), (indicators.get("^IRX") or {}).get("last"))

    depot_path = root / "depot.json"
    depot = json.loads(depot_path.read_text(encoding="utf-8")) if depot_path.is_file() else depot_core.empty_depot()
    symbols = [p["symbol"] for p in depot["positions"]] + [w["symbol"] for w in depot["watchlist"]]
    with ThreadPoolExecutor(max_workers=6) as pool:
        instruments = list(pool.map(_instrument, symbols))
    by_symbol = {i["symbol"]: i for i in instruments}

    weights: dict[str, float | None] = {}
    if depot["positions"]:
        base = depot["base_currency"]
        fx = {}
        for cur in {i["currency"] for i in instruments if i["currency"]} | {p["entry_currency"] for p in depot["positions"]}:
            if cur != base:
                rate = (_instrument(f"{cur}{base}=X")["quote"] or {}).get("price")
                if rate:
                    fx[cur] = rate
        valuation, _ = depot_core.value_depot(depot, {s: i["quote"] for s, i in by_symbol.items()}, fx)
        weights = {r["symbol"]: r["weight_pct"] for r in valuation["positions"]}

    positions = [by_symbol[p["symbol"]] for p in depot["positions"]]
    return {
        "indicators": {s: ({"name": bc.INDICATORS[s][0], "group": bc.INDICATORS[s][1], **v} if v else None)
                       for s, v in indicators.items()},
        "missing_indicators": missing,
        "vix_regime": bc.vix_regime(vix),
        "vix_regime_note": "VIX bands are a rule of thumb: <15 calm, 15–20 normal, 20–30 elevated, >30 stress.",
        "yield_curve": curve,
        "depot_exposure": bc.exposure(positions, weights) if positions else None,
        "holdings": [{k: i[k] for k in ("symbol", "name", "type", "sector", "country", "currency")} for i in instruments],
        "sources": [md.source(md.YAHOO, "https://finance.yahoo.com/markets", retrieved)],
        "not_covered": ["German/euro-area government bond yields (Bund)", "VSTOXX (euro-area volatility)",
                        "news, politics and central-bank communication"],
    }


def cmd_save(root: Path, stdin: str) -> dict[str, Any]:
    payload = json.loads(stdin)
    data = {k: payload.get(k) for k in ("regime", "indicators", "themes", "depot_impact")}
    bc.validate_brief(data)
    previous = (journal.load_entries(root, "market-brief", SUBJECT) or [None])[-1]
    saved, _ = journal.save_entry(root, "market-brief",
                                  {"subject": SUBJECT, "data": data, "report_markdown": payload.get("report_markdown")})
    return {"saved": saved["path"], "diff": bc.diff_briefs(previous["data"] if previous else None, data),
            "previous_created_at": previous["created_at"] if previous else None}


def main() -> int:
    parser = argparse.ArgumentParser(prog="brief.py")
    parser.add_argument("command", choices=("data", "save"))
    args = parser.parse_args()
    root = md.data_dir()
    result: dict[str, Any] = {"command": args.command, "ok": True, "error": None}
    try:
        result.update(cmd_data(root) if args.command == "data" else cmd_save(root, sys.stdin.read()))
    except (bc.BriefError, journal.JournalError, json.JSONDecodeError) as exc:
        result.update(ok=False, error=str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
