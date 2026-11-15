"""Pure logic for valuation: a simple two-stage DCF on free cash flow, its range and drivers, a reverse DCF,
and a peer-multiples comparison. No network I/O.

The DCF is deliberately simple (private-investor scope, ADR 0002): free cash flow after interest is treated as
cash to shareholders and discounted at the cost of equity (CAPM). Every assumption is returned with the result.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

YEARS = 10           # stage 1: years 1-5 at the start growth, years 6-10 fade linearly to the terminal growth
DEFAULT_TERMINAL = 0.02
DEFAULT_ERP = 0.05   # equity risk premium
BETA_FLOOR, BETA_CAP = 0.8, 2.0
GROWTH_FLOOR, GROWTH_CAP = -0.05, 0.20
NO_DCF_SECTORS = {"Financial Services"}  # banks and insurers: free cash flow says little
MULTIPLES = {  # key -> Yahoo info field
    "pe_trailing": "trailingPE",
    "pe_forward": "forwardPE",
    "ev_ebitda": "enterpriseToEbitda",
    "ev_sales": "enterpriseToRevenue",
    "price_to_book": "priceToBook",
}
FINANCIAL_MULTIPLES = ("pe_trailing", "pe_forward", "price_to_book")


class ValuationError(ValueError):
    pass


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _r(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


# --- inputs ----------------------------------------------------------------------------------------


def fcf_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annual rows {year, fcf, sbc} newest first, dropping years without a free cash flow."""
    out = [{"year": r["year"], "fcf": _num(r.get("fcf")), "sbc": _num(r.get("sbc"))} for r in rows]
    return [r for r in sorted(out, key=lambda r: r["year"], reverse=True) if r["fcf"] is not None]


def base_fcf(history: list[dict[str, Any]], method: str = "avg3") -> float | None:
    if not history:
        return None
    if method == "latest":
        return history[0]["fcf"]
    if method == "avg3":
        last = [r["fcf"] for r in history[:3]]
        return sum(last) / len(last)
    raise ValuationError("base FCF method must be 'latest' or 'avg3'")


def start_growth(growth_estimates: dict[str, Any], info: dict[str, Any]) -> tuple[float | None, str | None, list[str]]:
    """The stage-1 growth from analyst estimates: long-term growth, else next year's EPS growth, else
    the reported earnings growth. Clamped to a sane band, with a warning when clamped."""
    notes: list[str] = []
    candidates = [("analyst long-term growth (LTG)", _num(growth_estimates.get("LTG"))),
                  ("analyst EPS growth next year (+1y)", _num(growth_estimates.get("+1y"))),
                  ("reported earnings growth", _num(info.get("earningsGrowth")))]
    for label, value in candidates:
        if value is not None:
            clamped = min(max(value, GROWTH_FLOOR), GROWTH_CAP)
            if clamped != value:
                notes.append(f"Growth from {label} ({value:.1%}) clamped to {clamped:.1%}: no business grows that fast for 5 years.")
            return clamped, label, notes
    return None, None, ["No growth estimate available: pass --growth with a figure from a cited source."]


def discount_rate(risk_free: float, beta: float | None, erp: float = DEFAULT_ERP) -> tuple[float, dict[str, Any], list[str]]:
    """Cost of equity via CAPM: risk-free + beta x equity risk premium. Beta is clamped to [0.8, 2.0]."""
    notes: list[str] = []
    used = 1.0 if beta is None else min(max(beta, BETA_FLOOR), BETA_CAP)
    if beta is None:
        notes.append("No beta available: used 1.0 (market average).")
    elif used != beta:
        notes.append(f"Beta {beta:.2f} clamped to {used:.2f}: extreme betas are unstable.")
    rate = risk_free + used * erp
    return rate, {"risk_free": risk_free, "beta_reported": beta, "beta_used": used, "equity_risk_premium": erp}, notes


# --- DCF -------------------------------------------------------------------------------------------


def growth_path(g1: float, terminal: float, years: int = YEARS) -> list[float]:
    half = years // 2
    fade = [g1 + (terminal - g1) * (i + 1) / (years - half) for i in range(years - half)]
    return [g1] * half + fade


def dcf_value(fcf: float, g1: float, terminal: float, rate: float, years: int = YEARS) -> dict[str, float]:
    """Equity value: discounted cash flows of years 1..N plus a Gordon terminal value."""
    if rate <= terminal:
        raise ValuationError("The discount rate must be above the terminal growth.")
    cash, pv_years = fcf, 0.0
    for t, g in enumerate(growth_path(g1, terminal, years), start=1):
        cash *= 1 + g
        pv_years += cash / (1 + rate) ** t
    terminal_value = cash * (1 + terminal) / (rate - terminal)
    pv_terminal = terminal_value / (1 + rate) ** years
    total = pv_years + pv_terminal
    return {"equity_value": total, "pv_years": pv_years, "pv_terminal": pv_terminal,
            "terminal_share_pct": round(pv_terminal / total * 100, 1) if total else None}


def per_share(fcf: float, g1: float, terminal: float, rate: float, shares: float, fx: float = 1.0) -> float:
    return dcf_value(fcf, g1, terminal, rate)["equity_value"] / shares * fx


def value_range(fcf: float, g1: float, terminal: float, rate: float, shares: float, fx: float = 1.0) -> dict[str, float]:
    """Low/base/high: growth +-5 points and discount rate +-1 point, terminal growth fixed."""
    values = [per_share(fcf, g, terminal, d, shares, fx)
              for g in (g1 - 0.05, g1, g1 + 0.05) for d in (rate - 0.01, rate, rate + 0.01) if d > terminal]
    return {"low": round(min(values), 2), "base": round(per_share(fcf, g1, terminal, rate, shares, fx), 2),
            "high": round(max(values), 2)}


def sensitivity(fcf: float, g1: float, terminal: float, rate: float, shares: float, fx: float = 1.0) -> dict[str, Any]:
    """Fair value per share for discount rate (rows) x terminal growth (columns)."""
    rates = [round(rate + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    terms = [round(terminal + d, 4) for d in (-0.005, 0, 0.005)]
    grid = [[_r(per_share(fcf, g1, t, r, shares, fx)) if r > t else None for t in terms] for r in rates]
    return {"discount_rates": rates, "terminal_growths": terms, "values": grid}


def drivers(fcf: float, g1: float, terminal: float, rate: float, shares: float, fx: float = 1.0) -> list[dict[str, Any]]:
    """How much each assumption moves the base value, largest swing first (a tornado chart in numbers)."""
    base = per_share(fcf, g1, terminal, rate, shares, fx)
    tests = [
        ("growth years 1-5", "±5 points", (fcf, g1 - 0.05, terminal, rate), (fcf, g1 + 0.05, terminal, rate)),
        ("discount rate", "±1 point", (fcf, g1, terminal, rate + 0.01), (fcf, g1, terminal, rate - 0.01)),
        ("terminal growth", "±0.5 points", (fcf, g1, terminal - 0.005, rate), (fcf, g1, terminal + 0.005, rate)),
        ("starting free cash flow", "±20 %", (fcf * 0.8, g1, terminal, rate), (fcf * 1.2, g1, terminal, rate)),
    ]
    out = []
    for name, step, low_args, high_args in tests:
        low = per_share(*low_args, shares, fx)
        high = per_share(*high_args, shares, fx)
        out.append({"assumption": name, "step": step,
                    "low_pct": round((low / base - 1) * 100, 1), "high_pct": round((high / base - 1) * 100, 1),
                    "swing_pct": round((high - low) / base * 100, 1)})
    return sorted(out, key=lambda d: d["swing_pct"], reverse=True)


def implied_growth(price: float, fcf: float, terminal: float, rate: float, shares: float, fx: float = 1.0) -> float | None:
    """Reverse DCF: the years 1-5 growth the current price implies, holding the other assumptions."""
    lo, hi = -0.30, 0.60
    f = lambda g: per_share(fcf, g, terminal, rate, shares, fx) - price  # noqa: E731
    if f(lo) > 0 or f(hi) < 0:
        return None  # outside the searched band
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2, 4)


def dcf_applicable(info: dict[str, Any], fcf: float | None, shares: float | None) -> str | None:
    """None if a DCF makes sense, otherwise the reason it doesn't."""
    if (info.get("quoteType") or "").upper() == "ETF":
        return "ETFs hold many companies: a DCF doesn't apply. Look at the index valuation instead."
    if info.get("sector") in NO_DCF_SECTORS:
        return "Banks and insurers: free cash flow says little about them. Use P/B and P/E against peers."
    if not shares:
        return "Share count unavailable."
    if fcf is None:
        return "No free cash flow history from the source."
    if fcf <= 0:
        return "Free cash flow is negative: a DCF would need a turnaround forecast. Use peer multiples."
    return None


# --- peers -----------------------------------------------------------------------------------------


def multiples(info: dict[str, Any]) -> dict[str, float | None]:
    out = {}
    for key, field in MULTIPLES.items():
        v = _num(info.get(field))
        out[key] = v if v is not None and v > 0 else None  # a negative P/E is not a multiple
    return out


def compare_peers(target: dict[str, Any], peers: dict[str, dict[str, Any]], price: float | None) -> dict[str, Any]:
    """Target multiples against the peer median, with the price each median would imply."""
    keys = FINANCIAL_MULTIPLES if target.get("sector") in NO_DCF_SECTORS else tuple(MULTIPLES)
    own = multiples(target)
    peer_multiples = {s: multiples(i) for s, i in peers.items()}
    rows = []
    for k in keys:
        values = [m[k] for m in peer_multiples.values() if m[k] is not None]
        median = statistics.median(values) if values else None
        row = {"multiple": k, "target": _r(own[k]), "peer_median": _r(median), "peers_with_data": len(values),
               "premium_pct": None, "implied_price": None}
        if median and own[k]:
            row["premium_pct"] = round((own[k] / median - 1) * 100, 1)
            if price:
                row["implied_price"] = round(price * median / own[k], 2)
        rows.append(row)
    implied = [r["implied_price"] for r in rows if r["implied_price"] is not None]
    roe = None
    if target.get("sector") in NO_DCF_SECTORS:  # for banks, a P/B premium is earned by a higher return on equity
        pct = lambda i: _r(_num(i.get("returnOnEquity")) * 100, 1) if _num(i.get("returnOnEquity")) is not None else None  # noqa: E731
        peer_roe = [v for v in (pct(i) for i in peers.values()) if v is not None]
        roe = {"target_pct": pct(target), "peer_median_pct": _r(statistics.median(peer_roe), 1) if peer_roe else None,
               "peers_pct": {s: pct(i) for s, i in peers.items()}}
    return {"multiples": rows, "return_on_equity": roe,
            "peers": {s: {k: _r(v) for k, v in m.items() if k in keys} for s, m in peer_multiples.items()},
            "implied_range": {"low": min(implied), "median": _r(statistics.median(implied)), "high": max(implied)} if implied else None}
