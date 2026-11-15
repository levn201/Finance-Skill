"""Pure logic for the Depot Review: reuse decisions, ranking, validation and diff. No I/O."""

from __future__ import annotations

from datetime import date
from typing import Any

REUSE_MAX_AGE_DAYS = 7
REUSE_MAX_MOVE_PCT = 10.0
VIEWS = ("buy", "hold", "sell")
CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}
# What needs the investor's attention first: for Positions a sell, for buy candidates a buy.
VIEW_ORDER = {"depot": {"sell": 0, "buy": 1, "hold": 2}, "watchlist": {"buy": 0, "hold": 1, "sell": 2}}
LABELS = {
    "depot": {"buy": "Nachkaufen", "hold": "Halten", "sell": "Verkaufen"},
    "watchlist": {"buy": "Kaufen", "hold": "Abwarten", "sell": "Nicht kaufen"},
}


class ReviewError(ValueError):
    pass


def close_on(rows: list[tuple[str, float]], day: str) -> float | None:
    """Last close on or before `day` (ISO date)."""
    best = None
    for d, c in rows:
        if d <= day:
            best = c
        else:
            break
    return best


def reuse_decision(last: dict[str, Any] | None, today: date, price_now: float | None,
                   price_then: float | None, earnings_dates: list[str]) -> dict[str, Any]:
    """Whether the last Assessment can be reused instead of a fresh one, and why (not)."""
    if not last:
        return {"reuse": False, "reason": "no previous Assessment"}
    made = last["created_at"][:10]
    age = (today - date.fromisoformat(made)).days
    if age > REUSE_MAX_AGE_DAYS:
        return {"reuse": False, "reason": f"last Assessment is {age} days old", "age_days": age}
    if any(made < d <= today.isoformat() for d in earnings_dates):
        return {"reuse": False, "reason": "results were published since the last Assessment", "age_days": age}
    if price_now is None or price_then is None:
        return {"reuse": False, "reason": "price change since the last Assessment unknown", "age_days": age}
    move = round((price_now / price_then - 1) * 100, 2)
    if abs(move) > REUSE_MAX_MOVE_PCT:
        return {"reuse": False, "reason": f"price moved {move:+.1f}% since the last Assessment", "age_days": age, "move_pct": move}
    return {"reuse": True, "reason": f"{age} days old, price {move:+.1f}%, no results since", "age_days": age, "move_pct": move}


def rank(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Depot first, then Watchlist; inside each by urgency of the view, then by confidence."""
    def key(item: dict[str, Any]) -> tuple:
        group = 0 if item["in"] == "depot" else 1
        return (group, VIEW_ORDER[item["in"]][item["view"]], CONFIDENCE_ORDER.get(item.get("confidence"), 3), item["symbol"])
    ranked = sorted(items, key=key)
    return [{**item, "label": LABELS[item["in"]][item["view"]], "rank": i} for i, item in enumerate(ranked, 1)]


def validate_review(data: dict[str, Any], expected: dict[str, str]) -> None:
    """Every Position and Watchlist entry must be covered exactly once with a view and a one-line reason.

    expected: symbol -> "depot" | "watchlist"
    """
    items = data.get("items")
    if not isinstance(items, list):
        raise ReviewError("items must be a list")
    seen = {}
    for item in items:
        sym = str(item.get("symbol", "")).upper()
        if sym in seen:
            raise ReviewError(f"{sym} appears twice")
        if item.get("view") not in VIEWS:
            raise ReviewError(f"{sym}: view must be one of {', '.join(VIEWS)}")
        if not str(item.get("reason", "")).strip():
            raise ReviewError(f"{sym}: needs a one-line reason")
        if not isinstance(item.get("reused"), bool):
            raise ReviewError(f"{sym}: reused must be true or false")
        seen[sym] = item
    missing = sorted(set(expected) - set(seen))
    extra = sorted(set(seen) - set(expected))
    if missing:
        raise ReviewError(f"missing from the review: {', '.join(missing)}")
    if extra:
        raise ReviewError(f"not in Depot or Watchlist: {', '.join(extra)}")
    for sym, item in seen.items():
        if item.get("in") != expected[sym]:
            raise ReviewError(f"{sym}: 'in' must be {expected[sym]!r}")
    if not str(data.get("summary", "")).strip():
        raise ReviewError("summary must not be empty")


def diff_reviews(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if previous is None:
        return {"first": True, "changes": [], "added": [], "removed": []}
    prev = {i["symbol"]: i for i in previous["items"]}
    cur = {i["symbol"]: i for i in current["items"]}
    changes = [{"symbol": s, "from": prev[s]["view"], "to": cur[s]["view"], "in": cur[s]["in"]}
               for s in cur if s in prev and prev[s]["view"] != cur[s]["view"]]
    return {"first": False, "changes": changes,
            "added": sorted(set(cur) - set(prev)), "removed": sorted(set(prev) - set(cur))}
