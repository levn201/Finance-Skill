# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Sector facts. Prints one JSON object.

    uv run --script sector.py overview [--region us|europe|both]       # which sectors lead or lag the market
    uv run --script sector.py compare SAP.DE --peers ORCL MSFT CRM WDAY  # one company against its competitors
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
for sub in ("sector", "market-data"):
    sys.path.insert(0, str(HERE.parent.parent / sub / "scripts"))

import core as md  # noqa: E402
import providers  # noqa: E402
import sector_core as sc  # noqa: E402

MAX_PEERS = 12


def _info(symbol: str) -> tuple[str, dict[str, Any]]:
    try:
        return symbol, providers.yahoo_info(symbol)
    except Exception:
        return symbol, {}


def _summary(symbol: str) -> tuple[str, dict[str, Any]]:
    try:
        return symbol, md.summarize_history(providers.yahoo_history(symbol, "1y"))
    except Exception:
        return symbol, {}


def _parallel(fn, symbols):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(fn, symbols))


def overview(region: str, retrieved: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    sources = []
    groups = {"us": dict((etf, sec) for sec, etf in sc.US_SECTOR_ETFS.items()), "europe": sc.EUROPE_SECTOR_ETFS}
    for name in (("us", "europe") if region == "both" else (region,)):
        bench, bench_name = sc.BENCHMARKS[name]
        names = groups[name]
        summaries = _parallel(_summary, [bench, *names])
        b = summaries.get(bench, {})
        out[name] = {"benchmark": {"symbol": bench, "name": bench_name,
                                   **{f"return_{p}_pct": b.get(f"return_{p}_pct") for p in ("1m", "3m", "1y")}},
                     "sectors": sc.relative_performance(summaries, names, bench),
                     "missing": [s for s in names if not summaries.get(s)]}
        sources += [md.source(md.YAHOO, md.yahoo_url(s), retrieved) for s in (bench, *names)]
    return {"ok": True, "error": None, "mode": "overview", **out, "sources": sources,
            "notes": ["Sector ETFs stand in for the sectors: US Select Sector SPDRs and iShares STOXX Europe 600 sector ETFs."]}


def usd_factors(currencies: set[str]) -> dict[str, float | None]:
    out = {"USD": 1.0}
    for c in currencies - {"USD"}:
        _, info = _info(f"{c}USD=X")
        out[c] = md._num(info.get("regularMarketPrice"))
    return out


def compare(symbol: str, peers: list[str], retrieved: str) -> dict[str, Any]:
    symbols = [symbol, *[p for p in dict.fromkeys(s.upper() for s in peers) if p != symbol.upper()][:MAX_PEERS]]
    infos = _parallel(_info, symbols)
    missing = [s for s in symbols if not infos.get(s)]
    if symbol in missing:
        return {"ok": False, "error": f"No data for {symbol}."}
    infos = {s: i for s, i in infos.items() if i}
    histories = _parallel(_summary, list(infos))
    funds = {s: md.normalize_fundamentals(i) for s, i in infos.items()}
    fx = usd_factors({f["currency"] for f in funds.values() if f.get("currency")})
    revenue_usd = {}
    for s, i in infos.items():
        rev, factor = md._num(i.get("totalRevenue")), fx.get(funds[s].get("currency"))
        revenue_usd[s] = rev * factor if rev and factor else None
    result = sc.compare(symbol, funds, revenue_usd, {s: h.get("return_1y_pct") for s, h in histories.items()})
    target = infos[symbol]
    etfs = sc.sector_etfs(target.get("sector"), target.get("industry"))
    region = "europe" if sc.is_european(target.get("country")) else "us"
    etf = etfs[region] or etfs["us"]
    sector_perf = None
    if etf:
        bench = sc.BENCHMARKS["europe" if etf in sc.EUROPE_SECTOR_ETFS else "us"][0]
        label = sc.EUROPE_SECTOR_ETFS.get(etf) or target.get("sector")
        rows = sc.relative_performance(_parallel(_summary, [etf, bench]), {etf: label}, bench)
        sector_perf = {**rows[0], "benchmark": bench} if rows else None
    companies = {s: {"name": i.get("longName") or i.get("shortName"), "country": i.get("country"),
                     "industry": i.get("industry"), "currency": funds[s].get("currency"),
                     "market_cap": md._num(i.get("marketCap")), "quote_currency": i.get("currency"),
                     "revenue_usd": round(revenue_usd[s]) if revenue_usd[s] else None} for s, i in infos.items()}
    warnings = []
    if missing:
        warnings.append(f"No data for: {', '.join(missing)}.")
    if len(infos) < 4:
        warnings.append("Fewer than 3 competitors with data: ranks say little.")
    if result["revenue_share_note"]:
        warnings.append(result["revenue_share_note"])
    return {"ok": True, "error": None, "mode": "compare", "symbol": symbol,
            "sector": target.get("sector"), "industry": target.get("industry"), "sector_etfs": etfs,
            "sector_performance": sector_perf, "companies": companies,
            "comparison": {k: v for k, v in result.items() if k != "revenue_share_note"},
            "fx_to_usd": fx, "warnings": warnings,
            "notes": ["revenue_share_pct is the share of this group's combined revenue, not market share.",
                      "return_1y_pct is in each listing's own currency: exchange-rate moves are part of it."],
            "sources": [md.source(md.YAHOO, md.yahoo_url(s), retrieved) for s in infos]}


def main() -> int:
    parser = argparse.ArgumentParser(prog="sector.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("overview")
    o.add_argument("--region", choices=("us", "europe", "both"), default="both")
    c = sub.add_parser("compare")
    c.add_argument("symbol")
    c.add_argument("--peers", nargs="+", required=True)
    args = parser.parse_args()
    retrieved = md.now_iso()
    try:
        if args.cmd == "overview":
            result = overview(args.region, retrieved)
        else:
            ident = args.symbol.strip()
            symbol = providers.yahoo_symbol(ident.upper()) if md.is_isin(ident) else ident
            result = compare(symbol, args.peers, retrieved)
    except Exception as exc:
        result = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}",
                  "hints": ["Data source unreachable: take figures from web search, marked unverified (Lite Mode)."]}
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
