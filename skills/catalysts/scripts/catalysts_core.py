"""Pure logic for the Catalyst calendar: merge, sort, flag critical dates, diff against the last run."""

from __future__ import annotations

from datetime import date
from typing import Any

CRITICAL_DAYS = 14
EXTRA_TYPES = ("central_bank", "agm", "macro", "earnings", "ex_dividend", "other")


class CatalystError(ValueError):
    pass


def validate_extra(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Events found by web search (central-bank meetings, AGMs …). Each needs a date, title and source."""
    out = []
    for e in events:
        try:
            d = date.fromisoformat(str(e.get("date", ""))[:10])
        except ValueError:
            raise CatalystError(f"extra event {e.get('title')!r} needs an ISO date, got {e.get('date')!r}") from None
        if e.get("type") not in EXTRA_TYPES:
            raise CatalystError(f"extra event type must be one of {', '.join(EXTRA_TYPES)}, got {e.get('type')!r}")
        if not str(e.get("title", "")).strip():
            raise CatalystError("extra event needs a title")
        if not e.get("source") or not e.get("url"):
            raise CatalystError(f"extra event {e['title']!r} needs a source and url")
        out.append({
            "date": d.isoformat(),
            "type": e["type"],
            "symbol": (e.get("symbol") or "").upper() or None,
            "title": e["title"].strip(),
            "estimated": bool(e.get("estimated", False)),
            "source": e["source"],
            "url": e["url"],
        })
    return out


def build_calendar(per_symbol: dict[str, dict[str, Any]], context: dict[str, dict[str, Any]],
                   extra: list[dict[str, Any]], today: date, days: int,
                   critical_days: int = CRITICAL_DAYS) -> dict[str, Any]:
    """Upcoming events within `days`, sorted by date, with critical ones flagged.

    per_symbol: symbol -> {"events": [...], "warnings": [...]} as produced by market-data's normalize_catalysts
    context: symbol -> {"name": str|None, "in": "depot"|"watchlist"}
    """
    events: list[dict[str, Any]] = []
    warnings: list[str] = []
    no_upcoming: list[str] = []
    for symbol, result in per_symbol.items():
        ctx = context.get(symbol, {})
        upcoming = [e for e in result.get("events", []) if e.get("status") == "upcoming"]
        if not any(e["type"] == "earnings" for e in upcoming):
            no_upcoming.append(symbol)
        for e in upcoming:
            events.append({
                "date": e["date"],
                "type": e["type"],
                "symbol": symbol,
                "name": ctx.get("name"),
                "in": ctx.get("in"),
                "title": None,
                "estimated": bool(e.get("estimated", False)),
                "eps_estimate": e.get("eps_estimate"),
                "source": e.get("source"),
            })
        for w in result.get("warnings", []):
            if "AGM dates are not provided" not in w:  # said once below, not per symbol
                warnings.append(f"{symbol}: {w}")
    for e in extra:
        ctx = context.get(e["symbol"] or "", {})
        events.append({**e, "name": ctx.get("name"), "in": ctx.get("in")})

    horizon_end = date.fromordinal(today.toordinal() + days)
    in_window = []
    for e in events:
        d = date.fromisoformat(e["date"])
        if today <= d <= horizon_end:
            e["in_days"] = (d - today).days
            e["critical"] = e["in_days"] <= critical_days
            in_window.append(e)
    in_window.sort(key=lambda e: (e["date"], e["symbol"] or "", e["type"]))

    if per_symbol:
        warnings.append("AGM dates are not provided by the data sources; they come from web search only.")
    return {
        "as_of": today.isoformat(),
        "window_days": days,
        "critical_days": critical_days,
        "events": in_window,
        "critical_count": sum(1 for e in in_window if e["critical"]),
        "no_upcoming_earnings": sorted(no_upcoming),
        "warnings": warnings,
    }


def _key(e: dict[str, Any]) -> tuple[str, str, str]:
    return (e.get("symbol") or "", e["type"], e.get("title") or "")


def diff_calendars(previous: list[dict[str, Any]] | None, current: list[dict[str, Any]], today: date) -> dict[str, Any]:
    """New events, moved dates and events that disappeared since the last saved calendar."""
    if previous is None:
        return {"first": True, "new": [], "moved": [], "gone": []}
    prev = {_key(e): e for e in previous}
    cur = {_key(e): e for e in current}
    new = [cur[k] for k in cur if k not in prev]
    moved = [{"symbol": k[0] or None, "type": k[1], "title": k[2] or None, "from": prev[k]["date"], "to": cur[k]["date"]}
             for k in cur if k in prev and prev[k]["date"] != cur[k]["date"]]
    # an event that simply passed is not "gone"
    gone = [prev[k] for k in prev if k not in cur and prev[k]["date"] >= today.isoformat()]
    return {"first": False, "new": new, "moved": moved, "gone": gone}
