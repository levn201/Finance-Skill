# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Screen: find and rank Instruments by the investor's weighted criteria. Prints one JSON object.

    uv run --script screen.py --symbols RHM.DE HAG.DE SAAB-B.ST ... [--fit RHM.DE=95 HAG.DE=90 ...]
    uv run --script screen.py --region de [--sector Technology] [--min-mcap 2e9] [--size 40] [--any-country]

--fit SYMBOL=0-100 ...: how well each candidate fits the investor's theme, as judged from cited sources. Weights come from the Investor Profile (profile.json) unless --weights is given.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent
for sub in ("screen", "market-data"):
    sys.path.insert(0, str(SKILLS / sub / "scripts"))

import core as md  # noqa: E402
import providers  # noqa: E402
import screen_core as sc  # noqa: E402

MAX_CANDIDATES = 60


def _info(symbol: str) -> tuple[str, dict[str, Any]]:
    try:
        return symbol, providers.yahoo_info(symbol)
    except Exception:
        return symbol, {}


def _history(symbol: str) -> tuple[str, dict[str, Any]]:
    try:
        return symbol, md.summarize_history(providers.yahoo_history(symbol, "1y"))
    except Exception:
        return symbol, {}


def screener_quotes(region: str, sector: str | None, min_mcap: float | None, size: int) -> list[dict[str, Any]]:
    import yfinance as yf
    from yfinance import EquityQuery as Q

    exchange, _, _ = sc.REGIONS[region]
    parts = [Q("eq", ["region", region])]
    if exchange:
        parts.append(Q("eq", ["exchange", exchange]))
    else:
        parts.append(Q("is-in", ["exchange", *sc.US_MAIN_EXCHANGES]))
    if sector:
        parts.append(Q("eq", ["sector", sector]))
    if min_mcap:
        parts.append(Q("gt", ["intradaymarketcap", min_mcap]))
    result = yf.screen(Q("and", parts), sortField="intradaymarketcap", sortAsc=False, size=size)
    return result.get("quotes", [])


def load_weights(root: Path, override: list[str] | None) -> dict[str, int]:
    if override:
        weights = {}
        for pair in override:
            k, v = pair.split("=", 1)
            weights[k.strip()] = int(v)
        missing = set(sc.CRITERIA) - set(weights)
        if missing:
            raise sc.ScreenError(f"--weights must set all of: {', '.join(sc.CRITERIA)}")
        return weights
    profile = root / "profile.json"
    if profile.is_file():
        return json.loads(profile.read_text(encoding="utf-8"))["screening_weights"]
    return dict(sc.DEFAULT_WEIGHTS)


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = md.data_dir()
    retrieved = md.now_iso()
    result: dict[str, Any] = {"ok": True, "error": None, "notes": [], "dropped": []}
    weights = load_weights(root, args.weights)
    theme_fit = sc.parse_fit(args.fit) if args.fit else None

    if args.symbols:
        symbols = [s.upper() for s in dict.fromkeys(args.symbols)][:MAX_CANDIDATES]
        with ThreadPoolExecutor(max_workers=8) as pool:
            infos = dict(pool.map(_info, symbols))
        quotes = [{"symbol": s} for s in symbols]
        country = None
    else:
        if args.region not in sc.REGIONS:
            raise sc.ScreenError(f"region must be one of {', '.join(sc.REGIONS)}")
        _, home_country, home_currency = sc.REGIONS[args.region]
        raw = screener_quotes(args.region, args.sector, args.min_mcap, sc.SCREENER_FETCH)
        quotes = sc.prefilter_quotes(raw, None if args.any_country else home_currency, min(args.size, MAX_CANDIDATES))
        result["universe"] = {"screener_rows": len(raw), "after_prefilter": len(quotes)}
        with ThreadPoolExecutor(max_workers=8) as pool:
            infos = dict(pool.map(_info, [q["symbol"] for q in quotes]))
        country = None if args.any_country else home_country
    kept, dropped = sc.filter_candidates(quotes, infos, country)
    result["dropped"] = dropped

    with ThreadPoolExecutor(max_workers=8) as pool:
        histories = dict(pool.map(_history, kept))
    metrics = {s: sc.metrics_from(md.normalize_fundamentals(infos[s]), histories.get(s, {})) for s in kept}
    rows, notes = sc.score(metrics, weights, theme_fit)

    depot_path = root / "depot.json"
    depot = json.loads(depot_path.read_text(encoding="utf-8")) if depot_path.is_file() else {"positions": [], "watchlist": []}
    held = {p["symbol"] for p in depot["positions"]}
    watched = {w["symbol"] for w in depot["watchlist"]}
    for r in rows:
        info = infos[r["symbol"]]
        r.update(name=info.get("longName") or info.get("shortName"), sector=info.get("sector"),
                 country=info.get("country"), currency=info.get("currency"),
                 market_cap=md._num(info.get("marketCap")),
                 already="depot" if r["symbol"] in held else "watchlist" if r["symbol"] in watched else None)
    result.update(weights=weights, candidates=rows, notes=notes, sources=[md.source(md.YAHOO, "https://finance.yahoo.com/research-hub/screener", retrieved)])
    if len(rows) < 5:
        result["notes"].append("Fewer than 5 candidates: relative scores say little. Widen the universe.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="screen.py")
    universe = parser.add_mutually_exclusive_group(required=True)
    universe.add_argument("--symbols", nargs="+")
    universe.add_argument("--region")
    parser.add_argument("--sector")
    parser.add_argument("--min-mcap", type=float)
    parser.add_argument("--size", type=int, default=MAX_CANDIDATES)
    parser.add_argument("--any-country", action="store_true", help="Keep foreign companies listed in the region")
    parser.add_argument("--fit", nargs="+", help="Theme fit per candidate: SYMBOL=0-100 ...")
    parser.add_argument("--weights", nargs="+", help="fundamentals=30 valuation=25 dividend=15 thematic=15 technical=15")
    args = parser.parse_args()
    try:
        result = run(args)
    except (sc.ScreenError, ValueError, KeyError) as exc:
        result = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
    except Exception as exc:
        result = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}",
                  "hints": ["The screener may be unreachable here; build the candidate list by web search and use --symbols."]}
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
