# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Valuation of one stock: a simple DCF with its range, drivers and reverse DCF, plus a peer-multiples comparison.

    uv run --script valuation.py SAP.DE --risk-free 0.027 --peers ORCL MSFT CRM WDAY
    uv run --script valuation.py AAPL --peers MSFT GOOGL                      # USD: risk-free from ^TNX
    uv run --script valuation.py SAP.DE --risk-free 0.027 --growth 0.10 --terminal 0.02 --base-fcf latest

Assumptions not given are taken from the data and every one used is returned under "assumptions".
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
for sub in ("valuation", "market-data"):
    sys.path.insert(0, str(HERE.parent.parent / sub / "scripts"))

import core as md  # noqa: E402
import providers  # noqa: E402
import valuation_core as vc  # noqa: E402

SUBUNITS = {"GBp": ("GBP", 100), "GBX": ("GBP", 100), "ZAc": ("ZAR", 100), "ILA": ("ILS", 100)}
MAX_PEERS = 12


def _price(symbol: str) -> float | None:
    info = providers.yahoo_info(symbol)
    return md._num(info.get("regularMarketPrice") or info.get("previousClose"))


def fx_factor(financial: str | None, quote: str | None) -> tuple[float, str | None]:
    """Factor turning one unit of the reporting currency into the quote currency (incl. pence)."""
    if not financial or not quote:
        return 1.0, None
    major, mult = SUBUNITS.get(quote, (quote, 1))
    if financial == major:
        return float(mult), None
    pair = f"{financial}{major}=X"
    rate = _price(pair)
    if rate is None:
        raise vc.ValuationError(f"No exchange rate for {pair}.")
    return rate * mult, pair


def _peer(symbol: str) -> tuple[str, dict[str, Any]]:
    try:
        return symbol, providers.yahoo_info(symbol)
    except Exception:
        return symbol, {}


def run(args: argparse.Namespace) -> dict[str, Any]:
    ident = args.symbol.strip()
    symbol = providers.yahoo_symbol(ident.upper()) if md.is_isin(ident) else ident
    retrieved = md.now_iso()
    info = providers.yahoo_info(symbol)
    if not info:
        raise vc.ValuationError(f"No data for {symbol}.")
    quote = md.normalize_quote(info)
    price = quote.get("price")
    warnings: list[str] = []
    sources = [md.source(md.YAHOO, md.yahoo_url(symbol) + "/cash-flow", retrieved),
               md.source(md.YAHOO, md.yahoo_url(symbol) + "/analysis", retrieved)]
    result: dict[str, Any] = {"ok": True, "error": None, "symbol": symbol,
                              "name": info.get("longName") or info.get("shortName"),
                              "sector": info.get("sector"), "industry": info.get("industry"), "quote": quote}

    # --- DCF
    history = vc.fcf_history(providers.yahoo_cashflow(symbol))
    fcf = args.base_fcf_value if args.base_fcf_value is not None else vc.base_fcf(history, args.base_fcf)
    shares = md._num(info.get("sharesOutstanding") or info.get("impliedSharesOutstanding"))
    reason = vc.dcf_applicable(info, fcf, shares)
    result["fcf_history"] = history[:5]
    if history and history[0]["sbc"] and history[0]["fcf"] and history[0]["sbc"] / history[0]["fcf"] > 0.15:
        warnings.append(f"Stock-based pay is {history[0]['sbc'] / history[0]['fcf']:.0%} of the latest free cash flow: "
                        "it is a real cost to shareholders that free cash flow leaves out, so the DCF flatters.")
    if reason:
        result["dcf"] = {"applicable": False, "reason": reason}
    else:
        notes: list[str] = []
        if args.growth is not None:
            g1, g_source = args.growth, "given"
        else:
            g1, g_source, notes = vc.start_growth(providers.yahoo_growth_estimates(symbol), info)
        if args.discount is not None:
            rate, capm = args.discount, {"given": True}
        else:
            rf = args.risk_free
            if rf is None:
                if (info.get("financialCurrency") or info.get("currency")) != "USD":
                    raise vc.ValuationError(
                        "Pass --risk-free: the 10-year government bond yield for the reporting currency "
                        f"({info.get('financialCurrency')}), e.g. the German Bund for EUR, from a cited source.")
                tnx = _price("^TNX")
                if tnx is None:
                    raise vc.ValuationError("No US 10-year yield (^TNX). Pass --risk-free.")
                rf = tnx / 100
                sources.append(md.source(md.YAHOO, md.yahoo_url("^TNX"), retrieved))
            rate, capm, capm_notes = vc.discount_rate(rf, md._num(info.get("beta")), args.erp)
            notes += capm_notes
        if g1 is None:
            result["dcf"] = {"applicable": False, "reason": notes[-1]}
        else:
            fx, pair = fx_factor(info.get("financialCurrency"), info.get("currency"))
            if pair:
                sources.append(md.source(md.YAHOO, md.yahoo_url(pair), retrieved))
            core = vc.dcf_value(fcf, g1, args.terminal, rate)
            rng = vc.value_range(fcf, g1, args.terminal, rate, shares, fx)
            result["dcf"] = {
                "applicable": True,
                "assumptions": {"base_fcf": round(fcf), "base_fcf_method": "given" if args.base_fcf_value is not None else args.base_fcf,
                                "reporting_currency": info.get("financialCurrency"), "growth_years_1_5": round(g1, 4),
                                "growth_source": g_source, "growth_years_6_10": "linear fade to terminal",
                                "terminal_growth": args.terminal, "discount_rate": round(rate, 4), "capm": capm,
                                "shares": shares, "fx_to_quote_currency": round(fx, 6), "fx_pair": pair},
                "fair_value": rng,
                "upside_pct": round((rng["base"] / price - 1) * 100, 1) if price else None,
                "terminal_share_pct": core["terminal_share_pct"],
                "drivers": vc.drivers(fcf, g1, args.terminal, rate, shares, fx),
                "sensitivity": vc.sensitivity(fcf, g1, args.terminal, rate, shares, fx),
                "implied_growth_years_1_5": vc.implied_growth(price, fcf, args.terminal, rate, shares, fx) if price else None,
                "notes": notes,
            }
            if core["terminal_share_pct"] and core["terminal_share_pct"] > 75:
                warnings.append(f"{core['terminal_share_pct']} % of the value comes from beyond year 10: the result rests on long-run assumptions.")

    # --- peers
    if args.peers:
        peer_symbols = [p for p in dict.fromkeys(s.upper() for s in args.peers) if p != symbol.upper()][:MAX_PEERS]
        with ThreadPoolExecutor(max_workers=8) as pool:
            peers = dict(pool.map(_peer, peer_symbols))
        missing = [s for s, i in peers.items() if not i]
        if missing:
            warnings.append(f"No data for peers: {', '.join(missing)}.")
        result["peers"] = vc.compare_peers(info, {s: i for s, i in peers.items() if i}, price)
        for s in peers:
            sources.append(md.source(md.YAHOO, md.yahoo_url(s), retrieved))
        if len(peers) - len(missing) < 3:
            warnings.append("Fewer than 3 peers with data: the median says little.")
    else:
        result["peers"] = None
        result.setdefault("hints", []).append("No --peers given: find 4-8 listed competitors by web search and rerun with --peers.")

    result.update(sources=sources, warnings=warnings)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="valuation.py")
    parser.add_argument("symbol")
    parser.add_argument("--peers", nargs="+")
    parser.add_argument("--growth", type=float, help="Free cash flow growth for years 1-5, as a fraction (0.08)")
    parser.add_argument("--terminal", type=float, default=vc.DEFAULT_TERMINAL, help="Terminal growth (default 0.02)")
    parser.add_argument("--risk-free", type=float, help="10-year government bond yield as a fraction (0.027)")
    parser.add_argument("--erp", type=float, default=vc.DEFAULT_ERP, help="Equity risk premium (default 0.05)")
    parser.add_argument("--discount", type=float, help="Discount rate; overrides --risk-free/--erp and beta")
    parser.add_argument("--base-fcf", choices=("avg3", "latest"), default="avg3")
    parser.add_argument("--base-fcf-value", type=float, help="Starting free cash flow in the reporting currency")
    args = parser.parse_args()
    try:
        result = run(args)
    except vc.ValuationError as exc:
        result = {"ok": False, "error": str(exc)}
    except Exception as exc:
        result = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}",
                  "hints": ["Data source unreachable: take figures from web search, marked unverified (Lite Mode)."]}
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
