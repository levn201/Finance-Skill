"""Pure logic for Theses: record, revise, log data points, check, archive, and find gaps. No I/O."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any

SCHEMA_VERSION = 1
SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-=^]{0,19}$")
VERDICTS = ("intact", "weakened", "broken")
PILLAR_STATUSES = ("open", "holds", "at-risk", "broken")
IMPACTS = ("strengthens", "weakens", "neutral")
CONVICTIONS = ("high", "medium", "low")
HORIZONS = ("short-term", "medium-term")
REVIEW_AFTER_DAYS = 90
MIN_PILLARS, MAX_PILLARS = 1, 5


class ThesisError(ValueError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_store() -> dict[str, Any]:
    return {"version": SCHEMA_VERSION, "theses": {}}


def norm_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not SYMBOL_RE.match(s):
        raise ThesisError(f"'{symbol}' is not a valid symbol (e.g. SAP.DE, AAPL)")
    return s


def _choice(value: str | None, allowed: tuple[str, ...], name: str) -> str | None:
    if value is None:
        return None
    v = value.strip().lower()
    if v not in allowed:
        raise ThesisError(f"{name} must be one of {', '.join(allowed)}, got {value!r}")
    return v


def _text(value: str | None, name: str) -> str:
    if not value or not value.strip():
        raise ThesisError(f"{name} must not be empty")
    return value.strip()


def _pillars(texts: list[str]) -> list[dict[str, Any]]:
    texts = [t.strip() for t in texts if t and t.strip()]
    if not MIN_PILLARS <= len(texts) <= MAX_PILLARS:
        raise ThesisError(f"a Thesis needs {MIN_PILLARS} to {MAX_PILLARS} pillars, got {len(texts)}")
    return [{"id": i, "text": t, "status": "open"} for i, t in enumerate(texts, 1)]


def _id_map(pairs: list[str], allowed: tuple[str, ...], pillar_ids: set[int], name: str) -> dict[int, str]:
    """Parse ["1=holds", "2=at-risk"] into {1: "holds", 2: "at-risk"}."""
    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise ThesisError(f"{name} must look like <pillar number>=<value>, got {pair!r}")
        left, right = pair.split("=", 1)
        try:
            pid = int(left)
        except ValueError:
            raise ThesisError(f"pillar number must be a whole number, got {left!r}") from None
        if pid not in pillar_ids:
            raise ThesisError(f"there is no pillar {pid}; pillars are {sorted(pillar_ids)}")
        out[pid] = _choice(right, allowed, name)
    return out


def _active(store: dict[str, Any], symbol: str) -> dict[str, Any]:
    thesis = store["theses"].get(symbol)
    if not thesis or thesis["status"] != "active":
        raise ThesisError(f"no active Thesis for {symbol}; record one first")
    return thesis


def _log(thesis: dict[str, Any], kind: str, text: str, on: str | None = None, **extra: Any) -> None:
    thesis["log"].append({"date": on or date.today().isoformat(), "kind": kind, "text": text, **extra})
    thesis["updated_at"] = now_iso()


# --- operations --------------------------------------------------------------------------------


def record(store: dict, symbol: str, statement: str, pillars: list[str], exit_triggers: list[str],
           name: str | None = None, horizon: str | None = None, conviction: str | None = None) -> dict:
    store = deepcopy(store)
    sym = norm_symbol(symbol)
    existing = store["theses"].get(sym)
    if existing and existing["status"] == "active":
        raise ThesisError(f"{sym} already has an active Thesis; use revise to change it")
    triggers = [t.strip() for t in exit_triggers if t and t.strip()]
    if not triggers:
        raise ThesisError("a Thesis needs at least one exit trigger: what would prove it wrong?")
    thesis = {
        "symbol": sym,
        "name": name,
        "status": "active",
        "statement": _text(statement, "statement"),
        "pillars": _pillars(pillars),
        "exit_triggers": triggers,
        "horizon": _choice(horizon, HORIZONS, "horizon") or "medium-term",
        "conviction": _choice(conviction, CONVICTIONS, "conviction") or "medium",
        "verdict": "unchecked",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "last_checked_at": None,
        "log": list(existing["log"]) if existing else [],  # keep history of an archived Thesis
    }
    _log(thesis, "recorded", thesis["statement"])
    store["theses"][sym] = thesis
    return store


def revise(store: dict, symbol: str, reason: str, statement: str | None = None, pillars: list[str] | None = None,
           exit_triggers: list[str] | None = None, horizon: str | None = None, conviction: str | None = None) -> dict:
    """Change a Thesis deliberately. The previous version is kept in the log."""
    store = deepcopy(store)
    sym = norm_symbol(symbol)
    thesis = _active(store, sym)
    previous = {k: deepcopy(thesis[k]) for k in ("statement", "pillars", "exit_triggers", "horizon", "conviction")}
    if statement is not None:
        thesis["statement"] = _text(statement, "statement")
    if pillars:
        thesis["pillars"] = _pillars(pillars)
    if exit_triggers:
        thesis["exit_triggers"] = [t.strip() for t in exit_triggers if t.strip()]
    if horizon is not None:
        thesis["horizon"] = _choice(horizon, HORIZONS, "horizon")
    if conviction is not None:
        thesis["conviction"] = _choice(conviction, CONVICTIONS, "conviction")
    _log(thesis, "revised", _text(reason, "reason"), previous=previous)
    return store


def log_data_point(store: dict, symbol: str, text: str, impacts: list[str] | None = None,
                   sources: list[str] | None = None, on: str | None = None) -> dict:
    store = deepcopy(store)
    sym = norm_symbol(symbol)
    thesis = _active(store, sym)
    ids = {p["id"] for p in thesis["pillars"]}
    impact_map = _id_map(impacts or [], IMPACTS, ids, "impact")
    _log(thesis, "data_point", _text(text, "text"), on,
         pillar_impacts={str(k): v for k, v in impact_map.items()}, sources=sources or [])
    return store


def check(store: dict, symbol: str, verdict: str, summary: str, pillar_status: list[str] | None = None,
          conviction: str | None = None, sources: list[str] | None = None) -> dict:
    """Record the result of testing the Thesis against current facts."""
    store = deepcopy(store)
    sym = norm_symbol(symbol)
    thesis = _active(store, sym)
    v = _choice(verdict, VERDICTS, "verdict")
    ids = {p["id"] for p in thesis["pillars"]}
    for pid, status in _id_map(pillar_status or [], PILLAR_STATUSES, ids, "pillar status").items():
        next(p for p in thesis["pillars"] if p["id"] == pid)["status"] = status
    if v == "broken" and not any(p["status"] == "broken" for p in thesis["pillars"]) and not sources:
        raise ThesisError("a broken verdict needs a broken pillar or at least one source showing an exit trigger was hit")
    thesis["verdict"] = v
    if conviction is not None:
        thesis["conviction"] = _choice(conviction, CONVICTIONS, "conviction")
    thesis["last_checked_at"] = now_iso()
    _log(thesis, "check", _text(summary, "summary"), verdict=v,
         pillars={str(p["id"]): p["status"] for p in thesis["pillars"]}, sources=sources or [])
    return store


def archive(store: dict, symbol: str, reason: str) -> dict:
    """End a Thesis (e.g. the Position was sold). Its history is kept."""
    store = deepcopy(store)
    sym = norm_symbol(symbol)
    thesis = _active(store, sym)
    thesis["status"] = "archived"
    _log(thesis, "archived", _text(reason, "reason"))
    return store


# --- overview ----------------------------------------------------------------------------------


def gaps(store: dict, depot: dict | None, today: date) -> dict[str, list[dict[str, Any]]]:
    """What needs attention: Instruments without a Thesis, stale checks, Theses for sold Positions."""
    depot = depot or {"positions": [], "watchlist": []}
    held = {p["symbol"]: p.get("name") for p in depot.get("positions", [])}
    watched = {w["symbol"]: w.get("name") for w in depot.get("watchlist", [])}
    active = {s: t for s, t in store["theses"].items() if t["status"] == "active"}

    missing = [{"symbol": s, "name": n, "in": "depot"} for s, n in held.items() if s not in active]
    missing += [{"symbol": s, "name": n, "in": "watchlist"} for s, n in watched.items() if s not in active]

    stale = []
    for s, t in active.items():
        last = t["last_checked_at"] or t["created_at"]
        age = (today - date.fromisoformat(last[:10])).days
        if age >= REVIEW_AFTER_DAYS:
            stale.append({"symbol": s, "days_since_check": age, "never_checked": t["last_checked_at"] is None})

    orphaned = [{"symbol": s} for s in active if s not in held and s not in watched]
    return {"missing": missing, "due_for_review": stale, "not_in_depot_or_watchlist": orphaned}


def summary_row(thesis: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": thesis["symbol"],
        "name": thesis.get("name"),
        "status": thesis["status"],
        "verdict": thesis["verdict"],
        "conviction": thesis["conviction"],
        "statement": thesis["statement"],
        "pillars": [f"{p['id']}. {p['text']} [{p['status']}]" for p in thesis["pillars"]],
        "last_checked_at": thesis["last_checked_at"],
    }
