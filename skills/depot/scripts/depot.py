# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Depot and Watchlist CLI. Prints one JSON object per call.

    uv run --script depot.py show [--prices]
    uv run --script depot.py add SAP.DE --quantity 10 --entry-price 180 --name "SAP SE"
    uv run --script depot.py buy AAPL --quantity 5 --price 190 --currency EUR
    uv run --script depot.py sell SAP.DE --quantity 4      # omit --quantity to sell everything
    uv run --script depot.py update SAP.DE --entry-price 175.5
    uv run --script depot.py remove SAP.DE
    uv run --script depot.py watch ASML.AS --name "ASML Holding" --note "wait for a dip"
    uv run --script depot.py unwatch ASML.AS
    uv run --script depot.py base-currency EUR
    uv run --script depot.py snapshot
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import depot_core as dc  # noqa: E402

DATA_DIR_ENV = "FINANCIAL_SUPPORT_HOME"
DEPOT_FILE = "depot.json"


def _read_json(path: Path) -> Any:
    """Another skill's file (theses.json, profile.json), or None if missing or unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, ValueError):
        return None


def data_dir() -> Path:
    override = os.environ.get(DATA_DIR_ENV)
    return Path(override).expanduser() if override else Path.home() / ".financial-support"


def load(root: Path) -> dict[str, Any]:
    path = root / DEPOT_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else dc.empty_depot()


def save(root: Path, depot: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / (DEPOT_FILE + ".tmp")
    tmp.write_text(json.dumps(depot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(root / DEPOT_FILE)


def fetch_prices(depot: dict[str, Any]) -> tuple[dict, dict, list[dict], list[str]]:
    """Current quotes and FX rates through the market-data skill's provider layer."""
    sys.path.insert(0, str(HERE.parent.parent / "market-data" / "scripts"))
    import core as md_core  # type: ignore
    import providers  # type: ignore

    retrieved = md_core.now_iso()
    quotes, fx, warnings = {}, {}, []
    sources = [md_core.source(md_core.YAHOO, "https://finance.yahoo.com", retrieved)]
    base = depot["base_currency"]
    for pos in depot["positions"]:
        try:
            q = md_core.normalize_quote(providers.yahoo_info(pos["symbol"]))
            quotes[pos["symbol"]] = q
        except Exception as exc:
            warnings.append(f"Price for {pos['symbol']} failed ({exc.__class__.__name__}).")
    currencies = {dc.normalize_price(1, q["currency"])[1] for q in quotes.values() if q.get("currency")}
    currencies |= {p["entry_currency"] for p in depot["positions"]}
    for cur in sorted(currencies - {base}):
        try:
            rate = md_core.normalize_quote(providers.yahoo_info(f"{cur}{base}=X"))["price"]
            if rate:
                fx[cur] = rate
        except Exception as exc:
            warnings.append(f"Exchange rate {cur}->{base} failed ({exc.__class__.__name__}).")
    return quotes, fx, sources, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="depot.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("show")
    p.add_argument("--prices", action="store_true", help="Add current value, profit/loss and weights")
    for name in ("add", "update"):
        p = sub.add_parser(name)
        p.add_argument("symbol")
        p.add_argument("--quantity", type=float)
        p.add_argument("--entry-price", type=float)
        p.add_argument("--entry-currency")
        p.add_argument("--name")
        p.add_argument("--isin")
    p = sub.add_parser("buy")
    p.add_argument("symbol")
    p.add_argument("--quantity", type=float, required=True)
    p.add_argument("--price", type=float)
    p.add_argument("--currency")
    p = sub.add_parser("sell")
    p.add_argument("symbol")
    p.add_argument("--quantity", type=float)
    p = sub.add_parser("remove")
    p.add_argument("symbol")
    p = sub.add_parser("watch")
    p.add_argument("symbol")
    p.add_argument("--name")
    p.add_argument("--note")
    p = sub.add_parser("unwatch")
    p.add_argument("symbol")
    p = sub.add_parser("base-currency")
    p.add_argument("currency")
    sub.add_parser("snapshot")
    return parser


def run(argv: list[str]) -> dict[str, Any]:
    args = build_parser().parse_args(argv)
    root = data_dir()
    result: dict[str, Any] = {"command": args.command, "data_dir": str(root), "ok": True, "error": None,
                              "notes": [], "warnings": [], "sources": []}
    try:
        depot = load(root)
        changed = None
        if args.command == "add":
            changed = dc.add_position(depot, args.symbol, args.quantity, args.entry_price, args.entry_currency, args.name, args.isin)
        elif args.command == "update":
            changed = dc.update_position(depot, args.symbol, quantity=args.quantity, entry_price=args.entry_price,
                                         entry_currency=args.entry_currency, name=args.name, isin=args.isin)
        elif args.command == "buy":
            changed = dc.buy(depot, args.symbol, args.quantity, args.price, args.currency)
        elif args.command == "sell":
            changed = dc.sell(depot, args.symbol, args.quantity)
        elif args.command == "remove":
            changed = dc.remove_position(depot, args.symbol)
        elif args.command == "watch":
            changed = dc.watch(depot, args.symbol, args.name, args.note)
        elif args.command == "unwatch":
            changed = dc.unwatch(depot, args.symbol)
        elif args.command == "base-currency":
            changed = dc.set_base_currency(depot, args.currency)
        if changed:
            depot, result["notes"] = changed
            save(root, depot)
        result["depot"] = depot
        if args.command == "snapshot":
            theses = _read_json(root / "theses.json")
            result["snapshot"] = dc.render_snapshot(depot, dc.now_iso()[:10],
                                                    theses=(theses or {}).get("theses", {}),
                                                    profile=_read_json(root / "profile.json"))
        if args.command == "show" and args.prices and depot["positions"]:
            quotes, fx, sources, warnings = fetch_prices(depot)
            result["valuation"], more = dc.value_depot(depot, quotes, fx)
            result["sources"], result["warnings"] = sources, warnings + more
            result["fx_rates"] = fx
    except dc.DepotError as exc:
        result.update(ok=False, error=str(exc))
    except ImportError:
        result["warnings"].append("market-data is not available here, so no prices; showing the Depot without values.")
    return result


def main() -> int:
    result = run(sys.argv[1:])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
