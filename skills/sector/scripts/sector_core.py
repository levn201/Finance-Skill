"""Pure logic for sector: sector ETFs per Yahoo sector, sector performance relative to the market, and a
side-by-side comparison of one company with its competitors. No network I/O.
"""

from __future__ import annotations

import statistics
from typing import Any

BENCHMARKS = {"us": ("SPY", "S&P 500"), "europe": ("EXSA.DE", "STOXX Europe 600")}

# Yahoo sector -> US Select Sector SPDR ETF
US_SECTOR_ETFS = {
    "Technology": "XLK", "Healthcare": "XLV", "Financial Services": "XLF", "Industrials": "XLI",
    "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP", "Energy": "XLE", "Utilities": "XLU",
    "Basic Materials": "XLB", "Real Estate": "XLRE", "Communication Services": "XLC",
}

# iShares STOXX Europe 600 sector ETFs on Xetra: symbol -> STOXX supersector
EUROPE_SECTOR_ETFS = {
    "EXV3.DE": "Technology", "EXV4.DE": "Health Care", "EXV1.DE": "Banks", "EXH5.DE": "Insurance",
    "EXH2.DE": "Financial Services", "EXH4.DE": "Industrial Goods & Services", "EXV5.DE": "Automobiles & Parts",
    "EXH8.DE": "Retail", "EXV9.DE": "Travel & Leisure", "EXH7.DE": "Personal & Household Goods",
    "EXH3.DE": "Food & Beverage", "EXH1.DE": "Oil & Gas", "EXH9.DE": "Utilities", "EXV7.DE": "Chemicals",
    "EXV6.DE": "Basic Resources", "EXV8.DE": "Construction & Materials", "EXI5.DE": "Real Estate",
    "EXV2.DE": "Telecommunications", "EXH6.DE": "Media",
}

# Yahoo sector -> [(industry keyword, Europe ETF), ...], the first match wins; the last entry is the default
_EUROPE_BY_SECTOR = {
    "Technology": [("", "EXV3.DE")],
    "Healthcare": [("", "EXV4.DE")],
    "Financial Services": [("insurance", "EXH5.DE"), ("bank", "EXV1.DE"), ("", "EXH2.DE")],
    "Industrials": [("airline", "EXV9.DE"), ("building", "EXV8.DE"), ("engineering & construction", "EXV8.DE"), ("", "EXH4.DE")],
    "Consumer Cyclical": [("auto", "EXV5.DE"), ("retail", "EXH8.DE"), ("internet retail", "EXH8.DE"),
                          ("travel", "EXV9.DE"), ("lodging", "EXV9.DE"), ("resorts", "EXV9.DE"),
                          ("restaurants", "EXV9.DE"), ("", "EXH7.DE")],
    "Consumer Defensive": [("household", "EXH7.DE"), ("personal", "EXH7.DE"), ("tobacco", "EXH3.DE"), ("", "EXH3.DE")],
    "Energy": [("", "EXH1.DE")],
    "Utilities": [("", "EXH9.DE")],
    "Basic Materials": [("chemical", "EXV7.DE"), ("building materials", "EXV8.DE"), ("", "EXV6.DE")],
    "Real Estate": [("", "EXI5.DE")],
    "Communication Services": [("telecom", "EXV2.DE"), ("", "EXH6.DE")],
}

# Comparison metrics: key -> (where in normalize_fundamentals, higher is better?)
METRICS = {
    "revenue_growth_pct": (("growth", "revenue_growth_pct"), True),
    "earnings_growth_pct": (("growth", "earnings_growth_pct"), True),
    "gross_margin_pct": (("profitability", "gross_margin_pct"), True),
    "operating_margin_pct": (("profitability", "operating_margin_pct"), True),
    "profit_margin_pct": (("profitability", "profit_margin_pct"), True),
    "return_on_equity_pct": (("profitability", "return_on_equity_pct"), True),
    "debt_to_equity": (("balance_sheet", "debt_to_equity"), False),
    "pe_forward": (("valuation", "pe_forward"), False),
    "ev_to_ebitda": (("valuation", "ev_to_ebitda"), False),
    "dividend_yield_pct": (("dividend", "yield_pct"), True),
}
FINANCIAL_SKIP = {"gross_margin_pct", "operating_margin_pct", "debt_to_equity", "ev_to_ebitda"}  # meaningless for banks


def sector_etfs(sector: str | None, industry: str | None) -> dict[str, str | None]:
    """The US and the Europe sector ETF that best match a company's Yahoo sector and industry."""
    if not sector:
        return {"us": None, "europe": None}
    ind = (industry or "").lower()
    europe = next((etf for key, etf in _EUROPE_BY_SECTOR.get(sector, []) if key in ind), None)
    return {"us": US_SECTOR_ETFS.get(sector), "europe": europe}


def is_european(country: str | None) -> bool:
    return country not in (None, "United States", "Canada")


def relative_performance(summaries: dict[str, dict[str, Any]], names: dict[str, str], benchmark: str) -> list[dict[str, Any]]:
    """Sector ETF returns against the benchmark, strongest over 3 months first."""
    bench = summaries.get(benchmark, {})
    rows = []
    for sym, s in summaries.items():
        if sym == benchmark or s.get("insufficient_data") or not s:
            continue
        row = {"symbol": sym, "name": names.get(sym, sym)}
        for p in ("1m", "3m", "1y"):
            own, ref = s.get(f"return_{p}_pct"), bench.get(f"return_{p}_pct")
            row[f"return_{p}_pct"] = own
            row[f"vs_market_{p}_pts"] = None if own is None or ref is None else round(own - ref, 2)
        row["above_sma200"] = s.get("above_sma200")
        row["distance_from_high_pct"] = s.get("distance_from_high_pct")
        rows.append(row)
    return sorted(rows, key=lambda r: (r["vs_market_3m_pts"] is None, -(r["vs_market_3m_pts"] or 0)))


def _get(fund: dict[str, Any], path: tuple[str, str]) -> float | None:
    return (fund.get(path[0]) or {}).get(path[1])


def compare(target: str, funds: dict[str, dict[str, Any]], revenue_base: dict[str, float | None],
            returns_1y: dict[str, float | None]) -> dict[str, Any]:
    """Each metric for every company, the group median, and the target's rank (1 = best).

    revenue_base: revenue in one common currency per symbol (None if unknown), for the revenue share.
    """
    financial = (funds.get(target) or {}).get("sector") == "Financial Services"
    keys = [k for k in METRICS if not (financial and k in FINANCIAL_SKIP)]
    table: dict[str, dict[str, Any]] = {s: {k: _get(f, METRICS[k][0]) for k in keys} for s, f in funds.items()}
    for s in table:
        table[s]["return_1y_pct"] = returns_1y.get(s)
    keys.append("return_1y_pct")
    higher = {k: METRICS[k][1] if k in METRICS else True for k in keys}

    total_rev = sum(v for v in revenue_base.values() if v)
    known = [s for s, v in revenue_base.items() if v]
    for s in table:
        v = revenue_base.get(s)
        table[s]["revenue_share_pct"] = round(v / total_rev * 100, 1) if v and total_rev else None

    summary = []
    for k in keys:
        values = {s: row[k] for s, row in table.items() if row[k] is not None}
        own = table.get(target, {}).get(k)
        rank = None
        if own is not None:
            ordered = sorted(values.values(), reverse=higher[k])
            rank = ordered.index(own) + 1
        summary.append({"metric": k, "target": own, "median": round(statistics.median(values.values()), 2) if values else None,
                        "rank": rank, "of": len(values), "higher_is_better": higher[k]})
    strengths = [r["metric"] for r in summary if r["rank"] and r["of"] >= 3 and r["rank"] <= max(1, r["of"] // 3)]
    weaknesses = [r["metric"] for r in summary if r["rank"] and r["of"] >= 3 and r["rank"] > r["of"] - max(1, r["of"] // 3)]
    return {"table": table, "summary": summary, "strengths": strengths, "weaknesses": weaknesses,
            "revenue_share_note": None if len(known) == len(revenue_base) else
            f"Revenue share counts only the {len(known)} companies with revenue data."}
