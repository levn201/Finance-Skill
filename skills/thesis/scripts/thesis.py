# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Thesis CLI. Prints one JSON object per call. Data: <data dir>/theses.json.

    uv run --script thesis.py show [SYMBOL] [--all]
    uv run --script thesis.py gaps
    uv run --script thesis.py record SAP.DE --statement "..." --pillar "..." --pillar "..." --exit-trigger "..."
    uv run --script thesis.py revise SAP.DE --reason "..." [--statement ...] [--pillar ...] [--exit-trigger ...]
    uv run --script thesis.py log SAP.DE --text "Q3 cloud growth 27 %" --impact 1=strengthens --source <url>
    uv run --script thesis.py check SAP.DE --verdict intact --summary "..." --pillar-status 1=holds --source <url>
    uv run --script thesis.py archive SAP.DE --reason "sold"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import thesis_core as tc  # noqa: E402

DATA_DIR_ENV = "FINANCIAL_SUPPORT_HOME"
THESES_FILE = "theses.json"


def data_dir() -> Path:
    override = os.environ.get(DATA_DIR_ENV)
    return Path(override).expanduser() if override else Path.home() / ".financial-support"


def _read(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def save(root: Path, store: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / (THESES_FILE + ".tmp")
    tmp.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(root / THESES_FILE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thesis.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("show")
    p.add_argument("symbol", nargs="?")
    p.add_argument("--all", action="store_true", help="Include archived Theses")
    sub.add_parser("gaps")
    for name in ("record", "revise"):
        p = sub.add_parser(name)
        p.add_argument("symbol")
        p.add_argument("--statement", required=name == "record")
        p.add_argument("--pillar", action="append", default=[])
        p.add_argument("--exit-trigger", action="append", default=[])
        p.add_argument("--horizon")
        p.add_argument("--conviction")
        if name == "record":
            p.add_argument("--name")
        else:
            p.add_argument("--reason", required=True)
    p = sub.add_parser("log")
    p.add_argument("symbol")
    p.add_argument("--text", required=True)
    p.add_argument("--impact", action="append", default=[], help="<pillar>=strengthens|weakens|neutral")
    p.add_argument("--source", action="append", default=[])
    p.add_argument("--date", help="ISO date of the data point (default today)")
    p = sub.add_parser("check")
    p.add_argument("symbol")
    p.add_argument("--verdict", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--pillar-status", action="append", default=[], help="<pillar>=open|holds|at-risk|broken")
    p.add_argument("--conviction")
    p.add_argument("--source", action="append", default=[])
    p = sub.add_parser("archive")
    p.add_argument("symbol")
    p.add_argument("--reason", required=True)
    return parser


def run(argv: list[str]) -> dict[str, Any]:
    args = build_parser().parse_args(argv)
    root = data_dir()
    result: dict[str, Any] = {"command": args.command, "data_dir": str(root), "ok": True, "error": None}
    try:
        store = _read(root / THESES_FILE, tc.empty_store())
        new = None
        if args.command == "record":
            new = tc.record(store, args.symbol, args.statement, args.pillar, args.exit_trigger,
                            args.name, args.horizon, args.conviction)
        elif args.command == "revise":
            new = tc.revise(store, args.symbol, args.reason, args.statement, args.pillar, args.exit_trigger,
                            args.horizon, args.conviction)
        elif args.command == "log":
            if args.date:
                date.fromisoformat(args.date)
            new = tc.log_data_point(store, args.symbol, args.text, args.impact, args.source, args.date)
        elif args.command == "check":
            new = tc.check(store, args.symbol, args.verdict, args.summary, args.pillar_status, args.conviction, args.source)
        elif args.command == "archive":
            new = tc.archive(store, args.symbol, args.reason)
        if new is not None:
            save(root, new)
            store = new

        if args.command == "show":
            if args.symbol:
                sym = tc.norm_symbol(args.symbol)
                result["thesis"] = store["theses"].get(sym)
            else:
                result["theses"] = [tc.summary_row(t) for t in store["theses"].values()
                                    if args.all or t["status"] == "active"]
        elif args.command == "gaps":
            depot = _read(root / "depot.json", None)
            result["gaps"] = tc.gaps(store, depot, date.today())
            if depot is None:
                result["warnings"] = ["No Depot yet; tell the depot skill what you hold and watch."]
        else:
            result["thesis"] = store["theses"].get(tc.norm_symbol(args.symbol))
    except (tc.ThesisError, ValueError) as exc:
        result.update(ok=False, error=str(exc))
    return result


def main() -> int:
    result = run(sys.argv[1:])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
