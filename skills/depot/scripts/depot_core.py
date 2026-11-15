"""Pure logic for the Depot and Watchlist: changes, valuation and the Depot Snapshot. No I/O."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = 1
SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-=^]{0,19}$")
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
CONCENTRATION_THRESHOLD_PCT = 25.0
SNAPSHOT_HEADER = "FINANCIAL-SUPPORT DEPOT SNAPSHOT v1"


class DepotError(ValueError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_depot(base_currency: str = "EUR") -> dict[str, Any]:
    return {"version": SCHEMA_VERSION, "base_currency": base_currency, "positions": [], "watchlist": [], "updated_at": None}


# --- validation --------------------------------------------------------------------------------


def norm_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not SYMBOL_RE.match(s):
        raise DepotError(f"'{symbol}' is not a valid symbol; resolve it with market-data first (e.g. SAP.DE, AAPL)")
    return s


def norm_currency(currency: str) -> str:
    c = currency.strip().upper()
    if not CURRENCY_RE.match(c):
        raise DepotError(f"'{currency}' is not a currency code like EUR or USD")
    return c


def positive(value: Any, name: str) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise DepotError(f"{name} must be a number, got {value!r}") from None
    if not math.isfinite(f) or f <= 0:
        raise DepotError(f"{name} must be greater than 0, got {value!r}")
    return f


def _find(items: list[dict[str, Any]], symbol: str) -> dict[str, Any] | None:
    return next((i for i in items if i["symbol"] == symbol), None)


def _touch(depot: dict[str, Any]) -> None:
    depot["updated_at"] = now_iso()


# --- changes -----------------------------------------------------------------------------------


def add_position(depot: dict[str, Any], symbol: str, quantity: float | None = None, entry_price: float | None = None,
                 entry_currency: str | None = None, name: str | None = None, isin: str | None = None) -> tuple[dict, list[str]]:
    """Add a new Position. Quantity and entry price are optional. A Watchlist entry for it is removed."""
    depot = deepcopy(depot)
    sym = norm_symbol(symbol)
    if _find(depot["positions"], sym):
        raise DepotError(f"{sym} is already in the Depot; use buy to add shares or update to correct it")
    if isin is not None and not ISIN_RE.match(isin.strip().upper()):
        raise DepotError(f"'{isin}' is not a valid ISIN")
    notes = []
    position = {
        "symbol": sym,
        "name": name,
        "isin": isin.strip().upper() if isin else None,
        "quantity": positive(quantity, "quantity") if quantity is not None else None,
        "entry_price": positive(entry_price, "entry price") if entry_price is not None else None,
        "entry_currency": norm_currency(entry_currency) if entry_currency else depot["base_currency"],
        "added_at": now_iso(),
    }
    depot["positions"].append(position)
    if _find(depot["watchlist"], sym):
        depot["watchlist"] = [w for w in depot["watchlist"] if w["symbol"] != sym]
        notes.append(f"{sym} was removed from the Watchlist because it is now a Position.")
    _touch(depot)
    return depot, notes


def update_position(depot: dict[str, Any], symbol: str, **fields: Any) -> tuple[dict, list[str]]:
    """Correct fields of an existing Position (quantity, entry_price, entry_currency, name, isin)."""
    depot = deepcopy(depot)
    sym = norm_symbol(symbol)
    pos = _find(depot["positions"], sym)
    if not pos:
        raise DepotError(f"{sym} is not in the Depot")
    for key, value in fields.items():
        if value is None:
            continue
        if key in ("quantity", "entry_price"):
            pos[key] = positive(value, key.replace("_", " "))
        elif key == "entry_currency":
            pos[key] = norm_currency(value)
        elif key == "isin":
            if not ISIN_RE.match(value.strip().upper()):
                raise DepotError(f"'{value}' is not a valid ISIN")
            pos[key] = value.strip().upper()
        elif key == "name":
            pos[key] = value
        else:
            raise DepotError(f"unknown field {key!r}")
    _touch(depot)
    return depot, []


def buy(depot: dict[str, Any], symbol: str, quantity: float, price: float | None = None,
        currency: str | None = None) -> tuple[dict, list[str]]:
    """Add shares to a Position, or create it. The entry price becomes the quantity-weighted average."""
    sym = norm_symbol(symbol)
    qty = positive(quantity, "quantity")
    if not _find(depot["positions"], sym):
        return add_position(depot, sym, qty, price, currency)
    depot = deepcopy(depot)
    pos = _find(depot["positions"], sym)
    notes = []
    if currency and norm_currency(currency) != pos["entry_currency"]:
        raise DepotError(f"{sym} was bought in {pos['entry_currency']}; give the price in that currency")
    if pos["quantity"] is None:
        notes.append(f"The previous quantity of {sym} is unknown, so only the new shares are counted.")
        pos["quantity"], pos["entry_price"] = qty, positive(price, "price") if price is not None else None
    else:
        old_qty, old_price = pos["quantity"], pos["entry_price"]
        new_qty = old_qty + qty
        if price is not None and old_price is not None:
            pos["entry_price"] = round((old_qty * old_price + qty * positive(price, "price")) / new_qty, 6)
        elif price is None and old_price is not None:
            pos["entry_price"] = None
            notes.append(f"No price given for the new {sym} shares, so the average entry price is now unknown.")
        pos["quantity"] = new_qty
    _touch(depot)
    return depot, notes


def sell(depot: dict[str, Any], symbol: str, quantity: float | None = None) -> tuple[dict, list[str]]:
    """Reduce a Position. Without quantity, or when selling all shares, the Position is removed.

    The entry price of the remaining shares stays the same (average cost method).
    """
    depot = deepcopy(depot)
    sym = norm_symbol(symbol)
    pos = _find(depot["positions"], sym)
    if not pos:
        raise DepotError(f"{sym} is not in the Depot")
    if quantity is None:
        return remove_position(depot, sym)
    qty = positive(quantity, "quantity")
    if pos["quantity"] is None:
        raise DepotError(f"the quantity of {sym} is unknown; update it first or sell everything")
    if qty > pos["quantity"] + 1e-9:
        raise DepotError(f"cannot sell {qty:g} {sym}, only {pos['quantity']:g} held")
    if abs(qty - pos["quantity"]) < 1e-9:
        return remove_position(depot, sym)
    pos["quantity"] = round(pos["quantity"] - qty, 6)
    _touch(depot)
    return depot, []


def remove_position(depot: dict[str, Any], symbol: str) -> tuple[dict, list[str]]:
    depot = deepcopy(depot)
    sym = norm_symbol(symbol)
    if not _find(depot["positions"], sym):
        raise DepotError(f"{sym} is not in the Depot")
    depot["positions"] = [p for p in depot["positions"] if p["symbol"] != sym]
    _touch(depot)
    return depot, [f"{sym} was removed from the Depot."]


def watch(depot: dict[str, Any], symbol: str, name: str | None = None, note: str | None = None) -> tuple[dict, list[str]]:
    depot = deepcopy(depot)
    sym = norm_symbol(symbol)
    if _find(depot["positions"], sym):
        raise DepotError(f"{sym} is already a Position; the Watchlist is for Instruments you don't hold")
    if _find(depot["watchlist"], sym):
        raise DepotError(f"{sym} is already on the Watchlist")
    depot["watchlist"].append({"symbol": sym, "name": name, "note": note, "added_at": now_iso()})
    _touch(depot)
    return depot, []


def unwatch(depot: dict[str, Any], symbol: str) -> tuple[dict, list[str]]:
    depot = deepcopy(depot)
    sym = norm_symbol(symbol)
    if not _find(depot["watchlist"], sym):
        raise DepotError(f"{sym} is not on the Watchlist")
    depot["watchlist"] = [w for w in depot["watchlist"] if w["symbol"] != sym]
    _touch(depot)
    return depot, []


def set_base_currency(depot: dict[str, Any], currency: str) -> tuple[dict, list[str]]:
    depot = deepcopy(depot)
    depot["base_currency"] = norm_currency(currency)
    _touch(depot)
    return depot, []


# --- valuation ---------------------------------------------------------------------------------


def normalize_price(price: float, currency: str) -> tuple[float, str]:
    """Yahoo quotes London listings in pence (GBp) and Johannesburg in cents (ZAc)."""
    if currency == "GBp":
        return price / 100, "GBP"
    if currency == "ZAc":
        return price / 100, "ZAR"
    if currency == "ILA":
        return price / 100, "ILS"
    return price, currency.upper()


def value_depot(depot: dict[str, Any], quotes: dict[str, dict[str, Any]], fx: dict[str, float]) -> tuple[dict, list[str]]:
    """Value every Position in the base currency.

    quotes: symbol -> {"price": float|None, "currency": str|None, "name": str|None}
    fx: currency -> units of base currency per 1 unit of that currency (base itself is 1.0)
    """
    base = depot["base_currency"]
    fx = {**fx, base: 1.0}
    warnings: list[str] = []
    rows = []
    for pos in depot["positions"]:
        sym = pos["symbol"]
        q = quotes.get(sym) or {}
        row = {"symbol": sym, "name": pos.get("name") or q.get("name"), "type": q.get("type"), "quantity": pos["quantity"],
               "entry_price": pos["entry_price"], "entry_currency": pos["entry_currency"],
               "price": None, "price_currency": None, "value_base": None, "cost_base": None,
               "pnl_base": None, "pnl_pct": None, "weight_pct": None}
        if q.get("price") is None or not q.get("currency"):
            warnings.append(f"No current price for {sym}; it is left out of totals and weights.")
            rows.append(row)
            continue
        price, cur = normalize_price(float(q["price"]), q["currency"])
        row["price"], row["price_currency"] = round(price, 4), cur
        rate = fx.get(cur)
        if rate is None:
            warnings.append(f"No exchange rate {cur}->{base} for {sym}; it is left out of totals and weights.")
            rows.append(row)
            continue
        if pos["quantity"] is None:
            warnings.append(f"Quantity of {sym} unknown; no value or weight.")
            rows.append(row)
            continue
        row["value_base"] = round(pos["quantity"] * price * rate, 2)
        if pos["entry_price"] is not None:
            entry_rate = fx.get(pos["entry_currency"])
            if entry_rate is None:
                warnings.append(f"No exchange rate {pos['entry_currency']}->{base}; no profit/loss for {sym}.")
            else:
                row["cost_base"] = round(pos["quantity"] * pos["entry_price"] * entry_rate, 2)
                row["pnl_base"] = round(row["value_base"] - row["cost_base"], 2)
                row["pnl_pct"] = round((row["value_base"] / row["cost_base"] - 1) * 100, 2)
                if pos["entry_currency"] != base:
                    warnings.append(
                        f"{sym}: the entry price is in {pos['entry_currency']} and was converted at today's rate, "
                        "so the profit/loss in " + base + " ignores exchange-rate moves since the purchase."
                    )
        rows.append(row)

    total = sum(r["value_base"] for r in rows if r["value_base"] is not None)
    cost = sum(r["cost_base"] for r in rows if r["cost_base"] is not None)
    pnl_rows = [r for r in rows if r["pnl_base"] is not None]
    for r in rows:
        if r["value_base"] is not None and total > 0:
            r["weight_pct"] = round(r["value_base"] / total * 100, 2)
            # A broad ETF is diversified in itself, so a high weight is not a single-stock cluster risk.
            if r["weight_pct"] >= CONCENTRATION_THRESHOLD_PCT and len(rows) > 1 and r["type"] != "ETF":
                warnings.append(f"Concentration: {r['symbol']} is {r['weight_pct']:.1f}% of the valued Depot.")
    if pnl_rows and len(pnl_rows) < len(rows):
        warnings.append(
            f"Total profit/loss covers only {len(pnl_rows)} of {len(rows)} Positions; the others lack an entry price or price."
        )
    summary = {
        "base_currency": base,
        "total_value_base": round(total, 2),
        "total_cost_base": round(cost, 2) if pnl_rows else None,
        "total_pnl_base": round(sum(r["pnl_base"] for r in pnl_rows), 2) if pnl_rows else None,
        "pnl_positions": len(pnl_rows),
        "valued_positions": sum(1 for r in rows if r["value_base"] is not None),
        "positions": len(rows),
    }
    return {"summary": summary, "positions": rows}, warnings


# --- Depot Snapshot ----------------------------------------------------------------------------


def _fmt(value: float | None) -> str:
    return "?" if value is None else f"{value:g}"


def render_snapshot(depot: dict[str, Any], as_of: str) -> str:
    """A short read-only text copy of Depot and Watchlist for app chats (Lite Mode)."""
    lines = [f"{SNAPSHOT_HEADER} | as of {as_of} | base {depot['base_currency']}",
             "Read-only copy. Changes made in an app chat are not saved.", "", "POSITIONS"]
    if not depot["positions"]:
        lines.append("(none)")
    for p in depot["positions"]:
        entry = "?" if p["entry_price"] is None else f"{p['entry_price']:g} {p['entry_currency']}"
        lines.append(f"- {p['symbol']} | {p.get('name') or '?'} | qty {_fmt(p['quantity'])} | entry {entry}")
    lines += ["", "WATCHLIST"]
    if not depot["watchlist"]:
        lines.append("(none)")
    for w in depot["watchlist"]:
        note = f" | note: {w['note']}" if w.get("note") else ""
        lines.append(f"- {w['symbol']} | {w.get('name') or '?'}{note}")
    lines += ["", "END SNAPSHOT"]
    return "\n".join(lines)
