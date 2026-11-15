# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Daily run support. Prints one JSON object.

    uv run --script daily.py plan [--force]       # run today? Depot Review due? language, moves, recent results
    uv run --script daily.py save --input <inbox>/daily.json   # validate, store in the Journal (+ daily.md), diff

daily.json: {"headline": "...", "language": "de", "regime": "normal", "changes": ["..."],
  "upcoming": [{"date": "2026-11-17", "symbol": "NVDA", "event": "results"}], "actions": ["..."],
  "depot_review": {"ran": false, "reasons": []}, "report_markdown": "..."}
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
for sub in ("daily", "market-data", "assess"):
    sys.path.insert(0, str(HERE.parent.parent / sub / "scripts"))

import core as md  # noqa: E402
import daily_core as dc  # noqa: E402
import journal  # noqa: E402

KIND, SUBJECT = "daily", "DEPOT"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _last(root: Path, kind: str) -> dict[str, Any] | None:
    return (journal.load_entries(root, kind, SUBJECT) or [None])[-1]


def _market(symbol: str) -> tuple[str, float | None, str | None]:
    """1-day change in % and the date of the latest reported results."""
    import providers  # lazy: tests of `save` need no network stack
    try:
        move = md.normalize_quote(providers.yahoo_info(symbol)).get("change_pct")
    except Exception:
        move = None
    try:
        rows = providers.yahoo_earnings_dates(symbol, limit=4)
        reported = [r["date"] for r in rows if r.get("eps_reported") is not None]
        last = max(reported) if reported else None
    except Exception:
        last = None
    return symbol, move, last


def cmd_plan(root: Path, force: bool = False) -> dict[str, Any]:
    now = datetime.now().astimezone()
    today = now.date()
    last_daily = _last(root, KIND)
    run, why = dc.should_run(today, last_daily["created_at"] if last_daily else None)
    if force and not run:
        run, why = True, f"forced ({why})"
    profile = _read(root / "profile.json") or {}
    depot = _read(root / "depot.json") or {"positions": [], "watchlist": []}
    result: dict[str, Any] = {
        "run": run, "reason": why, "inbox": str(root / journal.INBOX_DIR), "now_local": now.isoformat(timespec="minutes"), "late_run": dc.is_late(now) and not force,
        "language": profile.get("language") or "en",
        "explanation_depth": profile.get("explanation_depth") or "beginner",
        "profile_missing": not profile,
        "positions": [p["symbol"] for p in depot["positions"]],
        "watchlist": [w["symbol"] for w in depot["watchlist"]],
    }
    if not run:
        return result
    symbols = result["positions"] + result["watchlist"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        market = list(pool.map(_market, symbols))
    moves = {s: m for s, m, _ in market}
    results = {s: d for s, _, d in market}
    last_review = _last(root, "depot-review")
    due, reasons = dc.review_due(today, last_review["created_at"] if last_review else None, moves, results)
    result.update(moves_1d_pct=moves, last_results=results, depot_review_due=due, depot_review_reasons=reasons,
                  last_daily_at=last_daily["created_at"] if last_daily else None,
                  last_depot_review_at=last_review["created_at"] if last_review else None)
    if not symbols:
        result["notes"] = ["The Depot and Watchlist are empty: the run covers only the Market Brief."]
    return result


def cmd_save(root: Path, stdin: str) -> dict[str, Any]:
    payload = json.loads(stdin)
    data = {k: payload.get(k) for k in ("headline", "language", "regime", "changes", "upcoming", "actions", "depot_review")}
    dc.validate_report(data)
    previous = _last(root, KIND)
    saved, _ = journal.save_entry(root, KIND, {"subject": SUBJECT, "data": data,
                                               "report_markdown": payload.get("report_markdown")})
    md_path = Path(saved["path"]).parent / "daily.md"
    md_path.write_text(payload.get("report_markdown") or data["headline"], encoding="utf-8")
    today = date.today()
    return {"saved": saved["path"], "report_file": str(md_path),
            "diff": dc.diff_reports(previous["data"] if previous else None, data),
            "critical_soon": dc.critical_soon(data["upcoming"], today)}


def main() -> int:
    parser = argparse.ArgumentParser(prog="daily.py")
    parser.add_argument("command", choices=("plan", "save"))
    parser.add_argument("--force", action="store_true", help="plan: run even on a weekend or a second time today")
    try:
        argv, text, path = journal.take_input(sys.argv[1:])
    except journal.JournalError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    args = parser.parse_args(argv)
    root = md.data_dir()
    result: dict[str, Any] = {"command": args.command, "ok": True, "error": None}
    try:
        result.update(cmd_plan(root, args.force) if args.command == "plan" else cmd_save(root, text if text is not None else sys.stdin.read()))
    except (dc.DailyError, journal.JournalError, json.JSONDecodeError) as exc:
        result.update(ok=False, error=str(exc))
    if result["ok"] and args.command == "save":
        journal.consume_input(root, path)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
