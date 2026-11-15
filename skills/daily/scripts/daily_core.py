"""Pure logic for the daily run: whether to run at all, whether a Depot Review is due, and the shape and diff of
the Daily Report. No I/O.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

MOVE_TRIGGER_PCT = 5.0       # a 1-day move of a Position or Watchlist entry at least this large triggers a review
RESULTS_WINDOW_DAYS = 3      # results reported in the last N days trigger a review
REVIEW_MAX_AGE_DAYS = 7      # a review older than this is due anyway
LATE_HOUR = 12               # a catch-up run after this local hour says so in the report
HEADLINE_MAX = 200           # phone notifications truncate beyond this


class DailyError(ValueError):
    pass


def should_run(today: date, last_daily: str | None) -> tuple[bool, str]:
    """Weekdays only, once a day (Desktop may start a catch-up run after sleep)."""
    if today.weekday() >= 5:
        return False, "weekend"
    if last_daily and last_daily[:10] == today.isoformat():
        return False, "already ran today"
    return True, "ok"


def review_due(today: date, last_review: str | None, moves: dict[str, float | None],
               last_results: dict[str, str | None]) -> tuple[bool, list[str]]:
    """Whether today's run includes a full Depot Review, and why.

    moves: 1-day change in % per symbol; last_results: date of the latest reported results per symbol.
    """
    reasons = []
    if today.weekday() == 0:
        reasons.append("Monday")
    if last_review is None:
        reasons.append("no Depot Review yet")
    elif (today - date.fromisoformat(last_review[:10])).days > REVIEW_MAX_AGE_DAYS:
        reasons.append(f"last Depot Review older than {REVIEW_MAX_AGE_DAYS} days")
    for sym, move in sorted(moves.items()):
        if move is not None and abs(move) >= MOVE_TRIGGER_PCT:
            reasons.append(f"{sym} moved {move:+.1f} % yesterday")
    for sym, d in sorted(last_results.items()):
        if d and 0 <= (today - date.fromisoformat(d[:10])).days <= RESULTS_WINDOW_DAYS:
            reasons.append(f"{sym} reported results on {d[:10]}")
    return bool(reasons), reasons


def is_late(now: datetime) -> bool:
    return now.hour >= LATE_HOUR


def validate_report(data: dict[str, Any]) -> None:
    headline = str(data.get("headline", "")).strip()
    if not headline:
        raise DailyError("headline is required: one line for the phone notification")
    if len(headline) > HEADLINE_MAX:
        raise DailyError(f"headline must be at most {HEADLINE_MAX} characters (it is {len(headline)})")
    if not isinstance(data.get("changes"), list):
        raise DailyError("changes must be a list (may be empty on a quiet day)")
    if not isinstance(data.get("upcoming"), list):
        raise DailyError("upcoming must be a list of {date, symbol, event}")
    for u in data["upcoming"]:
        if not (u.get("date") and u.get("event")):
            raise DailyError("every upcoming entry needs date and event")
    if not isinstance(data.get("actions"), list):
        raise DailyError("actions must be a list (may be empty)")
    if not isinstance(data.get("depot_review"), dict) or "ran" not in data["depot_review"]:
        raise DailyError("depot_review must say whether it ran: {\"ran\": true/false, \"reasons\": [...]}")
    if not data.get("language"):
        raise DailyError("language is required (the Investor Profile default)")


def diff_reports(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if previous is None:
        return {"first": True}
    prev_actions = {str(a).strip().lower() for a in previous.get("actions", [])}
    cur_actions = {str(a).strip().lower() for a in current.get("actions", [])}
    prev_up = {(u["date"], u.get("symbol"), u["event"]) for u in previous.get("upcoming", [])}
    return {
        "first": False,
        "regime": None if previous.get("regime") == current.get("regime")
        else {"from": previous.get("regime"), "to": current.get("regime")},
        "new_actions": [a for a in current.get("actions", []) if str(a).strip().lower() not in prev_actions],
        "dropped_actions": [a for a in previous.get("actions", []) if str(a).strip().lower() not in cur_actions],
        "new_upcoming": [u for u in current.get("upcoming", []) if (u["date"], u.get("symbol"), u["event"]) not in prev_up],
    }


def critical_soon(upcoming: list[dict[str, Any]], today: date, days: int = 2) -> list[dict[str, Any]]:
    end = today + timedelta(days=days)
    return [u for u in upcoming if today <= date.fromisoformat(u["date"][:10]) <= end]
