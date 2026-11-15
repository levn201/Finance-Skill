# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""The Journal: dated record of outputs, used to show what changed since the previous run.

Layout: <data dir>/journal/<YYYY-MM-DD>/<kind>-<subject>-<HHMMSS>.json

    uv run --script journal.py save assessment < entry.json   # validates, stores, returns the diff to the last one
    uv run --script journal.py last assessment SAP.DE
    uv run --script journal.py history assessment SAP.DE [--limit 10]

An entry on stdin is {"subject": "SAP.DE", "data": {...}, "report_markdown": "..."}.
Other skills (catalysts, market-brief) use the same script with their own kind.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR_ENV = "FINANCIAL_SUPPORT_HOME"
KIND_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
SUBJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-=^_]{0,39}$")

VIEWS = ("buy", "hold", "sell")
DIRECTIONS = ("positive", "neutral", "negative", "uncertain")
CONFIDENCE = ("high", "medium", "low")
CONTEXTS = ("position", "watchlist", "other")
THESIS_VERDICTS = ("intact", "weakened", "broken", "unchecked", "none")
HORIZONS = ("short-term", "medium-term")
FORBIDDEN_KEYS = {"position_size", "quantity_to_buy", "quantity_to_sell", "allocation_pct", "target_weight"}


class JournalError(ValueError):
    pass


# --- input files -------------------------------------------------------------------------------
# Unattended runs can't pass JSON on the command line (Claude Code blocks `{"` in shell commands), so every
# script that reads JSON on stdin also takes `--input <file>`. Agents write such files to <data dir>/inbox/.

INBOX_DIR = "inbox"


def take_input(argv: list[str]) -> tuple[list[str], str | None, Path | None]:
    """Pop `--input PATH` from argv: (remaining argv, the file's text, its path), or (argv, None, None)."""
    if "--input" not in argv:
        return argv, None, None
    i = argv.index("--input")
    if i + 1 >= len(argv):
        raise JournalError("--input needs a file path")
    path = Path(argv[i + 1]).expanduser()
    if not path.is_file():
        raise JournalError(f"input file not found: {path}")
    return argv[:i] + argv[i + 2:], path.read_text(encoding="utf-8"), path


def consume_input(root: Path, path: Path | None) -> None:
    """Delete an input file after a successful save, but only if it lies in <data dir>/inbox/."""
    if path is not None and path.resolve().parent == (root / INBOX_DIR).resolve():
        path.unlink(missing_ok=True)


def data_dir(environ: dict[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    override = env.get(DATA_DIR_ENV)
    return Path(override).expanduser() if override else Path.home() / ".financial-support"


# --- validation --------------------------------------------------------------------------------


def _req_list(data: dict, key: str, minimum: int = 1) -> list:
    value = data.get(key)
    if not isinstance(value, list) or len([v for v in value if v]) < minimum:
        raise JournalError(f"{key} needs at least {minimum} entr{'y' if minimum == 1 else 'ies'}")
    return value


def _enum(data: dict, key: str, allowed: tuple[str, ...]) -> None:
    if data.get(key) not in allowed:
        raise JournalError(f"{key} must be one of {', '.join(allowed)}, got {data.get(key)!r}")


def _walk_keys(obj: Any) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | set().union(*(_walk_keys(v) for v in obj.values())) if obj else set()
    if isinstance(obj, list):
        return set().union(*(_walk_keys(v) for v in obj)) if obj else set()
    return set()


def validate_assessment(data: dict[str, Any]) -> None:
    """The shape every Assessment must have (GLOSSARY: Assessment, Outlook, Horizon)."""
    _enum(data, "view", VIEWS)
    _enum(data, "context", CONTEXTS)
    _enum(data, "horizon_basis", HORIZONS)
    _enum(data, "confidence", CONFIDENCE)
    _enum(data, "thesis_verdict", THESIS_VERDICTS)
    outlooks = data.get("outlooks")
    if not isinstance(outlooks, dict) or set(outlooks) != set(HORIZONS):
        raise JournalError("outlooks needs exactly one entry per Horizon: short-term and medium-term")
    for horizon, outlook in outlooks.items():
        _enum(outlook, "direction", DIRECTIONS)
        if not str(outlook.get("summary", "")).strip():
            raise JournalError(f"outlooks.{horizon}.summary must not be empty")
        _req_list(outlook, "drivers")
    _req_list(data, "reasons_for")
    _req_list(data, "reasons_against")
    _req_list(data, "invalidation")
    for source in _req_list(data, "sources"):
        if not isinstance(source, dict) or not source.get("name") or not (source.get("retrieved_at") or source.get("as_of")):
            raise JournalError("every source needs a name and a retrieved_at or as_of date")
    for figure in data.get("key_figures", []):
        if figure.get("value") is not None and not (figure.get("source") and figure.get("as_of")):
            raise JournalError(f"key figure {figure.get('label')!r} needs a source and an as_of date")
    forbidden = _walk_keys(data) & FORBIDDEN_KEYS
    if forbidden:
        raise JournalError(f"Assessments never include position sizes; remove {', '.join(sorted(forbidden))}")


VALIDATORS = {"assessment": validate_assessment}


# --- diff --------------------------------------------------------------------------------------


def diff_assessment(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if previous is None:
        return {"first": True, "changes": []}
    prev, cur = previous["data"], current["data"]
    changes = []
    if prev["view"] != cur["view"]:
        changes.append({"field": "view", "from": prev["view"], "to": cur["view"]})
    for h in HORIZONS:
        a, b = prev["outlooks"][h]["direction"], cur["outlooks"][h]["direction"]
        if a != b:
            changes.append({"field": f"outlook.{h}", "from": a, "to": b})
    for key in ("thesis_verdict", "confidence"):
        if prev.get(key) != cur.get(key):
            changes.append({"field": key, "from": prev.get(key), "to": cur.get(key)})
    days = (datetime.fromisoformat(current["created_at"]) - datetime.fromisoformat(previous["created_at"])).days
    return {"first": False, "previous_created_at": previous["created_at"], "days_since": days, "changes": changes}


DIFFERS = {"assessment": diff_assessment}


# --- storage -----------------------------------------------------------------------------------


def _entries(root: Path, kind: str, subject: str) -> list[Path]:
    journal = root / "journal"
    if not journal.is_dir():
        return []
    safe = subject.upper()
    return sorted(journal.glob(f"*/{kind}-{safe}-*.json"), key=lambda p: (p.parent.name, p.name))


def load_entries(root: Path, kind: str, subject: str) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in _entries(root, kind, subject)]


def save_entry(root: Path, kind: str, entry: dict[str, Any], now: datetime | None = None) -> tuple[dict, dict]:
    if not KIND_RE.match(kind):
        raise JournalError(f"invalid kind {kind!r}")
    subject = str(entry.get("subject", "")).strip().upper()
    if not SUBJECT_RE.match(subject):
        raise JournalError(f"invalid subject {entry.get('subject')!r}")
    data = entry.get("data")
    if not isinstance(data, dict):
        raise JournalError("entry needs a data object")
    if kind in VALIDATORS:
        VALIDATORS[kind](data)
    now = now or datetime.now(timezone.utc)
    previous = (load_entries(root, kind, subject) or [None])[-1]
    record = {
        "kind": kind,
        "subject": subject,
        "created_at": now.replace(microsecond=0).isoformat(),
        "data": data,
        "report_markdown": entry.get("report_markdown"),
    }
    day_dir = root / "journal" / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / f"{kind}-{subject}-{now.strftime('%H%M%S')}.json"
    counter = 1
    while path.exists():
        path = day_dir / f"{kind}-{subject}-{now.strftime('%H%M%S')}-{counter}.json"
        counter += 1
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    diff = DIFFERS[kind](previous, record) if kind in DIFFERS else {"first": previous is None}
    return {**record, "path": str(path)}, diff


# --- CLI ---------------------------------------------------------------------------------------


def run(argv: list[str], stdin: str | None = None, environ: dict[str, str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="journal.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("save")
    p.add_argument("kind")
    for name in ("last", "history"):
        p = sub.add_parser(name)
        p.add_argument("kind")
        p.add_argument("subject")
        if name == "history":
            p.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    root = data_dir(environ)
    result: dict[str, Any] = {"command": args.command, "ok": True, "error": None}
    try:
        if args.command == "save":
            try:
                entry = json.loads(stdin or "")
            except json.JSONDecodeError as exc:
                raise JournalError(f"stdin is not valid JSON: {exc}") from None
            saved, diff = save_entry(root, args.kind, entry)
            result.update(saved=saved["path"], diff=diff)
        elif args.command == "last":
            entries = load_entries(root, args.kind, args.subject)
            result["entry"] = entries[-1] if entries else None
        else:
            entries = load_entries(root, args.kind, args.subject)[-args.limit:]
            result["entries"] = [{"created_at": e["created_at"], "data": e["data"]} for e in entries]
    except JournalError as exc:
        result.update(ok=False, error=str(exc))
    return result


def main() -> int:
    try:
        argv, text, path = take_input(sys.argv[1:])
    except JournalError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    stdin = text if text is not None else (sys.stdin.read() if argv[:1] == ["save"] else None)
    result = run(argv, stdin)
    if result["ok"]:
        consume_input(data_dir(), path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
