"""Pure logic for a Screen: candidate filtering and weighted scoring. No I/O.

Scores are relative: each metric is ranked against the other candidates (percentile 0–100), so a Screen
answers "which of these look best on my criteria", not "is this cheap in absolute terms".
"""

from __future__ import annotations

from typing import Any

CRITERIA = ("fundamentals", "valuation", "dividend", "thematic", "technical")
DEFAULT_WEIGHTS = {"fundamentals": 30, "valuation": 25, "dividend": 15, "thematic": 15, "technical": 15}

# Region -> (home exchange code for the Yahoo screener, home country as Yahoo reports it, reporting currency)
REGIONS = {
    "us": (None, "United States", "USD"),
    "de": ("GER", "Germany", "EUR"),
    "fr": ("PAR", "France", "EUR"),
    "nl": ("AMS", "Netherlands", "EUR"),
    "gb": ("LSE", "United Kingdom", "GBP"),
    "ch": ("EBS", "Switzerland", "CHF"),
    "it": ("MIL", "Italy", "EUR"),
    "es": ("MCE", "Spain", "EUR"),
    "at": ("VIE", "Austria", "EUR"),
    "be": ("BRU", "Belgium", "EUR"),
    "dk": ("CPH", "Denmark", "DKK"),
    "fi": ("HEL", "Finland", "EUR"),
    "se": ("STO", "Sweden", "SEK"),
    "no": ("OSL", "Norway", "NOK"),
}
SCREENER_FETCH = 250  # one screener call; candidates are narrowed before any per-symbol lookups


def prefilter_quotes(quotes: list[dict[str, Any]], currency: str | None, limit: int) -> list[dict[str, Any]]:
    """Cheap first pass on screener rows: same reporting currency as the home country, OTC dropped.

    Foreign companies listed in the region (e.g. Apple on Xetra) report in their own currency, so this removes
    most of them before the per-symbol data is fetched. The country check afterwards is still authoritative.
    """
    out = []
    for q in quotes:
        if q.get("exchange") in OTC_EXCHANGES:
            continue
        if currency and q.get("financialCurrency") and q["financialCurrency"] != currency:
            continue
        out.append(q)
        if len(out) >= limit:
            break
    return out
US_MAIN_EXCHANGES = ("NMS", "NYQ", "NGM", "NCM", "ASE")
OTC_EXCHANGES = {"PNK", "OQB", "OQX", "OEM", "OGM"}

# metric -> (criterion, higher_is_better)
METRICS = {
    "revenue_growth_pct": ("fundamentals", True),
    "operating_margin_pct": ("fundamentals", True),
    "return_on_equity_pct": ("fundamentals", True),
    "debt_to_equity": ("fundamentals", False),
    "pe_forward": ("valuation", False),
    "ev_to_ebitda": ("valuation", False),
    "peg": ("valuation", False),
    "dividend_yield_pct": ("dividend", True),
    "payout_health": ("dividend", True),
    "return_6m_pct": ("technical", True),
    "return_1y_pct": ("technical", True),
    "sma200_trend": ("technical", True),
}


class ScreenError(ValueError):
    pass


def parse_fit(pairs: list[str]) -> dict[str, float]:
    """Parse ["RHM.DE=95", "AIR.PA=55"] into {"RHM.DE": 95.0, ...}; values must be 0–100."""
    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise ScreenError(f"--fit expects SYMBOL=0-100, got {pair!r}")
        sym, value = pair.split("=", 1)
        try:
            v = float(value)
        except ValueError:
            raise ScreenError(f"theme fit for {sym} must be a number, got {value!r}") from None
        if not 0 <= v <= 100:
            raise ScreenError(f"theme fit for {sym} must be between 0 and 100, got {v:g}")
        out[sym.strip().upper()] = v
    return out


def filter_candidates(quotes: list[dict[str, Any]], infos: dict[str, dict[str, Any]],
                      country: str | None) -> tuple[list[str], list[dict[str, str]]]:
    """Keep primary listings of companies from `country`; drop OTC listings and duplicates of the same company."""
    kept, dropped, seen_names = [], [], set()
    for q in quotes:
        sym = q["symbol"]
        info = infos.get(sym) or {}
        name = (info.get("longName") or q.get("longName") or q.get("shortName") or sym).strip().lower()
        if (info.get("exchange") or q.get("exchange")) in OTC_EXCHANGES:
            dropped.append({"symbol": sym, "reason": "OTC listing"})
        elif country and info.get("country") != country:
            dropped.append({"symbol": sym, "reason": f"company based in {info.get('country') or 'unknown'}, not {country}"})
        elif name in seen_names:
            dropped.append({"symbol": sym, "reason": "another listing of the same company"})
        elif not info:
            dropped.append({"symbol": sym, "reason": "no data"})
        else:
            kept.append(sym)
            seen_names.add(name)
    return kept, dropped


FINANCIAL_SECTORS = {"Financial Services"}
NOT_MEANINGFUL_FOR_FINANCIALS = ("debt_to_equity", "ev_to_ebitda")  # debt is the business model of banks/insurers


def metrics_from(fundamentals: dict[str, Any], history: dict[str, Any]) -> dict[str, float | None]:
    """The raw metrics used for scoring. Negative or meaningless valuation ratios become None.

    For banks and insurers, leverage and EV/EBITDA are left out: they are not comparable to other companies.
    """
    metrics = _metrics(fundamentals, history)
    if fundamentals.get("sector") in FINANCIAL_SECTORS:
        for key in NOT_MEANINGFUL_FOR_FINANCIALS:
            metrics[key] = None
    return metrics


def _metrics(fundamentals: dict[str, Any], history: dict[str, Any]) -> dict[str, float | None]:
    v, g, p, b, d = (fundamentals.get(k, {}) for k in ("valuation", "growth", "profitability", "balance_sheet", "dividend"))

    def positive(x):
        return x if isinstance(x, (int, float)) and x > 0 else None

    payout = d.get("payout_ratio_pct")
    # Paying out more than earned (or nearly all of it) is a warning sign; 30–70 % counts as healthy.
    payout_health = None if payout is None or not d.get("yield_pct") else (
        100.0 if 30 <= payout <= 70 else 70.0 if payout < 30 else 40.0 if payout <= 90 else 0.0)
    trend = history.get("above_sma200")
    return {
        "revenue_growth_pct": g.get("revenue_growth_pct"),
        "operating_margin_pct": p.get("operating_margin_pct"),
        "return_on_equity_pct": p.get("return_on_equity_pct"),
        "debt_to_equity": b.get("debt_to_equity"),
        "pe_forward": positive(v.get("pe_forward")),
        "ev_to_ebitda": positive(v.get("ev_to_ebitda")),
        "peg": positive(v.get("peg")),
        "dividend_yield_pct": d.get("yield_pct") if d.get("yield_pct") is not None else (0.0 if fundamentals else None),
        "payout_health": payout_health,
        "return_6m_pct": history.get("return_6m_pct"),
        "return_1y_pct": history.get("return_1y_pct"),
        "sma200_trend": None if trend is None else (100.0 if trend else 0.0),
    }


def _percentiles(values: dict[str, float | None], higher_is_better: bool) -> dict[str, float]:
    present = {s: v for s, v in values.items() if v is not None}
    if len(present) < 2:
        return {s: 50.0 for s in present}  # nothing to compare against
    ordered = sorted(present.values())
    out = {}
    for s, v in present.items():
        below = sum(1 for x in ordered if x < v)
        equal = sum(1 for x in ordered if x == v)
        pct = (below + (equal - 1) / 2) / (len(ordered) - 1) * 100
        out[s] = round(pct if higher_is_better else 100 - pct, 1)
    return out


def score(metrics: dict[str, dict[str, float | None]], weights: dict[str, int],
          theme_fit: dict[str, float] | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """Rank candidates by the weighted average of their criterion scores.

    metrics: symbol -> raw metrics (see metrics_from)
    theme_fit: symbol -> 0–100 fit to the investor's theme, judged from sources; None = no theme given
    A criterion without data for a candidate is left out of that candidate's average, and its weight is
    spread over the others; `coverage_pct` shows how much of the intended weight had data.
    """
    if set(weights) != set(CRITERIA):
        raise ScreenError(f"weights must have exactly: {', '.join(CRITERIA)}")
    notes = []
    weights = dict(weights)
    if theme_fit is None and weights["thematic"]:
        notes.append(f"No theme given, so the thematic weight ({weights['thematic']}) was spread over the other criteria.")
        weights["thematic"] = 0
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ScreenError("at least one criterion needs a weight above 0")

    per_metric = {m: _percentiles({s: metrics[s].get(m) for s in metrics}, hib) for m, (_, hib) in METRICS.items()}
    rows = []
    for sym in metrics:
        crit: dict[str, float | None] = {}
        for c in CRITERIA:
            if c == "thematic":
                crit[c] = None if theme_fit is None or sym not in theme_fit else float(theme_fit[sym])
                continue
            scores = [per_metric[m][sym] for m, (mc, _) in METRICS.items() if mc == c and sym in per_metric[m]]
            crit[c] = round(sum(scores) / len(scores), 1) if scores else None
        used = {c: weights[c] for c in CRITERIA if weights[c] and crit[c] is not None}
        used_weight = sum(used.values())
        total = round(sum(crit[c] * w for c, w in used.items()) / used_weight, 1) if used_weight else None
        rows.append({"symbol": sym, "score": total, "criteria": crit,
                     "coverage_pct": round(used_weight / total_weight * 100), "metrics": metrics[sym]})
    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0), r["symbol"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows, notes
