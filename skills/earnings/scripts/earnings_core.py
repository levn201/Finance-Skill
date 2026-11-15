"""Pure logic for earnings previews and reviews: track record, price reactions, consensus, revisions."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

RECENT_RESULTS_DAYS = 10  # results this recent switch the default from preview to review


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def split_dates(rows: list[dict[str, Any]], today: date) -> tuple[list[dict], list[dict]]:
    """(reported, upcoming): reported have an EPS, newest first; upcoming are in the future, soonest first."""
    reported = sorted((r for r in rows if _num(r.get("eps_reported")) is not None), key=lambda r: r["date"], reverse=True)
    upcoming = sorted((r for r in rows if _num(r.get("eps_reported")) is None and r["date"] >= today.isoformat()),
                      key=lambda r: r["date"])
    return reported, upcoming


def price_reaction(closes: list[tuple[str, float]], day: str) -> dict[str, Any] | None:
    """Move from the last close before `day` to the first close after it.

    The two-day window covers both pre-market and after-hours releases without knowing the exact time.
    """
    before = [(d, c) for d, c in closes if d < day]
    after = [(d, c) for d, c in closes if d > day]
    if not before or not after:
        return None
    (d0, c0), (d1, c1) = before[-1], after[0]
    if (date.fromisoformat(d1) - date.fromisoformat(d0)).days > 7:
        return None  # gap in the price history; don't pretend
    return {"from": d0, "to": d1, "move_pct": round((c1 / c0 - 1) * 100, 2)}


def track_record(reported: list[dict[str, Any]], closes: list[tuple[str, float]], quarters: int = 8) -> dict[str, Any]:
    rows = []
    for r in reported[:quarters]:
        surprise = _num(r.get("surprise_pct"))
        rows.append({
            "date": r["date"],
            "eps_estimate": _num(r.get("eps_estimate")),
            "eps_reported": _num(r.get("eps_reported")),
            "surprise_pct": None if surprise is None else round(surprise, 2),
            "beat": None if surprise is None else surprise > 0,
            "reaction": price_reaction(closes, r["date"]),
        })
    surprises = [r["surprise_pct"] for r in rows if r["surprise_pct"] is not None]
    moves = [r["reaction"]["move_pct"] for r in rows if r["reaction"]]
    beats_with_drop = [r["date"] for r in rows if r["beat"] and r["reaction"] and r["reaction"]["move_pct"] < 0]
    return {
        "quarters": rows,
        "beat_rate_pct": round(sum(1 for s in surprises if s > 0) / len(surprises) * 100) if surprises else None,
        "avg_surprise_pct": round(sum(surprises) / len(surprises), 2) if surprises else None,
        "avg_abs_move_pct": round(sum(abs(m) for m in moves) / len(moves), 2) if moves else None,
        "max_abs_move_pct": round(max(abs(m) for m in moves), 2) if moves else None,
        "beat_but_fell": beats_with_drop,
    }


def consensus(estimates: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Current-quarter (0q) and current-year (0y) consensus, plus how the quarter's EPS estimate moved."""
    def period(rows, key):
        return next((r for r in rows if r.get("index") == key), None)

    def eps(p):
        r = period(estimates.get("eps", []), p)
        return None if not r else {"avg": _num(r.get("avg")), "low": _num(r.get("low")), "high": _num(r.get("high")),
                                   "analysts": _num(r.get("numberOfAnalysts")), "year_ago": _num(r.get("yearAgoEps")),
                                   "growth_pct": None if _num(r.get("growth")) is None else round(_num(r.get("growth")) * 100, 2),
                                   "currency": r.get("currency")}

    def revenue(p):
        r = period(estimates.get("revenue", []), p)
        return None if not r else {"avg": _num(r.get("avg")), "low": _num(r.get("low")), "high": _num(r.get("high")),
                                   "analysts": _num(r.get("numberOfAnalysts")), "year_ago": _num(r.get("yearAgoRevenue")),
                                   "growth_pct": None if _num(r.get("growth")) is None else round(_num(r.get("growth")) * 100, 2),
                                   "currency": r.get("currency")}

    trend = period(estimates.get("eps_trend", []), "0q")
    revision = None
    if trend and _num(trend.get("current")) and _num(trend.get("90daysAgo")):
        change_30 = (_num(trend["current"]) / _num(trend["30daysAgo"]) - 1) * 100 if _num(trend.get("30daysAgo")) else None
        change_90 = (_num(trend["current"]) / _num(trend["90daysAgo"]) - 1) * 100
        direction = "up" if change_90 > 1 else "down" if change_90 < -1 else "flat"
        revision = {"change_30d_pct": None if change_30 is None else round(change_30, 2),
                    "change_90d_pct": round(change_90, 2), "direction": direction}
    return {"quarter_eps": eps("0q"), "quarter_revenue": revenue("0q"), "year_eps": eps("0y"),
            "year_revenue": revenue("0y"), "eps_revision": revision}


def default_mode(reported: list[dict[str, Any]], today: date) -> str:
    """'review' if results came out in the last RECENT_RESULTS_DAYS days, otherwise 'preview'."""
    if reported and date.fromisoformat(reported[0]["date"]) >= today - timedelta(days=RECENT_RESULTS_DAYS):
        return "review"
    return "preview"
