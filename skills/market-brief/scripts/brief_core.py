"""Pure logic for the Market Brief: indicator summaries, volatility regime, Depot exposure, validation, diff."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

INDICATORS = {
    "^GSPC": ("S&P 500", "equity"),
    "^NDX": ("Nasdaq 100", "equity"),
    "^GDAXI": ("DAX", "equity"),
    "^STOXX50E": ("Euro Stoxx 50", "equity"),
    "^VIX": ("VIX (US equity volatility)", "volatility"),
    "^MOVE": ("MOVE (US bond volatility)", "volatility"),
    "^TNX": ("US 10-year yield (%)", "rates"),
    "^IRX": ("US 3-month yield (%)", "rates"),
    "EURUSD=X": ("EUR/USD", "fx"),
    "DX-Y.NYB": ("US dollar index", "fx"),
    "BZ=F": ("Brent crude (USD)", "commodity"),
    "GC=F": ("Gold (USD)", "commodity"),
}
# Common rule-of-thumb bands for the VIX; a convention, not a law.
VIX_BANDS = ((15, "calm"), (20, "normal"), (30, "elevated"))
REGIMES = ("calm", "normal", "elevated", "stress")
CATEGORIES = ("macro", "central_banks", "politics", "geopolitics", "trade", "sector", "other")
DIRECTIONS = ("positive", "neutral", "negative", "uncertain")


class BriefError(ValueError):
    pass


def indicator_summary(rows: list[tuple[str, float]]) -> dict[str, Any] | None:
    """Last value, changes over 1 day / 1 week / 1 month, and where the last value sits in its 1-year range."""
    closes = [c for _, c in rows if c is not None and c == c]
    if len(closes) < 2:
        return None
    last = closes[-1]

    def change(back: int) -> float | None:
        if len(closes) <= back or closes[-1 - back] == 0:
            return None
        return round((last / closes[-1 - back] - 1) * 100, 2)

    lo, hi = min(closes), max(closes)
    percentile = round(sum(1 for c in closes if c <= last) / len(closes) * 100)
    sma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None
    return {
        "last": round(last, 4),
        "as_of": rows[-1][0],
        "change_1d_pct": change(1),
        "change_1w_pct": change(5),
        "change_1m_pct": change(21),
        "range_1y": [round(lo, 4), round(hi, 4)],
        "percentile_1y": percentile,
        "above_sma200": None if sma200 is None else last > sma200,
    }


def vix_regime(vix: float | None) -> str | None:
    if vix is None:
        return None
    for limit, name in VIX_BANDS:
        if vix < limit:
            return name
    return "stress"


def yield_curve(ten_year: float | None, three_month: float | None) -> dict[str, Any] | None:
    if ten_year is None or three_month is None:
        return None
    spread = round(ten_year - three_month, 2)
    return {"spread_10y_3m_pct_points": spread, "inverted": spread < 0}


def exposure(items: list[dict[str, Any]], weights: dict[str, float | None]) -> dict[str, Any]:
    """Depot mix by sector, country and currency, weighted by value where known.

    items: [{"symbol", "sector", "country", "currency", "type"}] for Positions
    weights: symbol -> weight_pct (None when the value is unknown)
    """
    out: dict[str, dict[str, float]] = {"sector": defaultdict(float), "country": defaultdict(float), "currency": defaultdict(float)}
    unweighted = []
    for item in items:
        w = weights.get(item["symbol"])
        if w is None:
            unweighted.append(item["symbol"])
            continue
        sector = "ETF / diversified" if item.get("type") == "ETF" else (item.get("sector") or "unknown")
        out["sector"][sector] += w
        out["country"][item.get("country") or ("ETF / diversified" if item.get("type") == "ETF" else "unknown")] += w
        out["currency"][item.get("currency") or "unknown"] += w
    return {
        dim: dict(sorted(((k, round(v, 1)) for k, v in vals.items()), key=lambda kv: -kv[1]))
        for dim, vals in out.items()
    } | {"not_weighted": unweighted}


def validate_brief(data: dict[str, Any]) -> None:
    if data.get("regime") not in REGIMES:
        raise BriefError(f"regime must be one of {', '.join(REGIMES)}")
    themes = data.get("themes")
    if not isinstance(themes, list) or not themes:
        raise BriefError("themes needs at least one entry")
    for t in themes:
        if not str(t.get("title", "")).strip():
            raise BriefError("every theme needs a title")
        if t.get("category") not in CATEGORIES:
            raise BriefError(f"theme {t.get('title')!r}: category must be one of {', '.join(CATEGORIES)}")
        if t.get("direction") not in DIRECTIONS:
            raise BriefError(f"theme {t['title']!r}: direction must be one of {', '.join(DIRECTIONS)}")
        if not isinstance(t.get("affects"), list):
            raise BriefError(f"theme {t['title']!r}: affects must be a list of symbols (may be empty)")
        if not t.get("sources"):
            raise BriefError(f"theme {t['title']!r} needs at least one source")
    if not str(data.get("depot_impact", "")).strip():
        raise BriefError("depot_impact must say what the situation means for the Depot and Watchlist")


def diff_briefs(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if previous is None:
        return {"first": True}
    prev_titles = {t["title"].strip().lower(): t for t in previous.get("themes", [])}
    cur_titles = {t["title"].strip().lower(): t for t in current.get("themes", [])}
    vix_then = (previous.get("indicators", {}).get("^VIX") or {}).get("last")
    vix_now = (current.get("indicators", {}).get("^VIX") or {}).get("last")
    return {
        "first": False,
        "regime": None if previous["regime"] == current["regime"] else {"from": previous["regime"], "to": current["regime"]},
        "vix": None if vix_then is None or vix_now is None else {"from": vix_then, "to": vix_now},
        "new_themes": [cur_titles[k]["title"] for k in cur_titles if k not in prev_titles],
        "dropped_themes": [prev_titles[k]["title"] for k in prev_titles if k not in cur_titles],
        "direction_changes": [
            {"title": cur_titles[k]["title"], "from": prev_titles[k]["direction"], "to": cur_titles[k]["direction"]}
            for k in cur_titles if k in prev_titles and prev_titles[k]["direction"] != cur_titles[k]["direction"]
        ],
    }
