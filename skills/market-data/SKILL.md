---
name: market-data
description: Fetches figures for stocks and ETFs (price, price history, fundamentals, dividend, earnings and ex-dividend dates, SEC filings) as JSON with sources, and tells you whether you are in full mode or Lite Mode. Use it whenever another financial-support skill (assess, catalysts, earnings, screen, valuation, depot-review, market-brief, sector) needs a number about an Instrument. Never state such a figure from memory.
---

# market-data

Internal helper. The investor never calls it directly. Other skills use it to get **figures**. News, politics and context come from web search, not from here (ADR 0003).

## 1. Decide the mode first

Once per conversation, before you fetch any figure, run:

```bash
uv run --script <this skill's directory>/scripts/fetch.py status
```

- **Full mode**: the command runs and `data.mode` is `"full"`. Use the commands below for all figures.
- **Lite Mode**: the command can't run (no shell, no `uv`, sandbox without network), or `data.mode` is `"lite"`. Follow the Lite Mode rules in section 5.

If `uv` is missing but Python ≥ 3.11 with `yfinance` is installed, `python3 scripts/fetch.py …` works too.

Pass any `hints` from `status` on to the investor once, briefly. Examples: no Investor Profile yet, or no Finnhub key. Don't repeat them for every call.

## 2. Commands

All commands print one JSON envelope.

| Command | Use for |
|---|---|
| `resolve "<name, ticker or ISIN>"` | Finding the right symbol before anything else when the investor names a company |
| `quote <instrument>` | Current price, daily change, 52-week range, market cap |
| `fundamentals <instrument>` | Valuation (P/E, PEG, P/B, EV/EBITDA), growth, margins, balance sheet, dividend, analyst targets; `etf` block for ETFs |
| `history <instrument> [--period 1y] [--raw]` | Returns over 1/3/6/12 months, volatility, max drawdown, SMA50/SMA200 |
| `catalysts <instrument>` | Next earnings date (with EPS/revenue estimates) and ex-dividend date |
| `filings <US ticker> [--limit 10]` | Recent 10-K, 10-Q, 8-K, 20-F, 6-K and proxy filings (US registrants only) |

Here `<instrument>` is a Yahoo symbol or an ISIN:
- US stocks use the plain ticker (`AAPL`).
- Xetra listings use `.DE` (`SAP.DE`), and Euronext Amsterdam uses `.AS`.
- An ISIN is resolved automatically (`DE0007164600`).
- When the investor holds a German or EU stock, prefer its home listing in EUR over a US ADR.

## 3. Reading the envelope

```json
{"command": "...", "instrument": "SAP.DE", "ok": true, "error": null,
 "data": {...}, "sources": [{"name": "...", "url": "...", "retrieved_at": "..."}],
 "warnings": ["..."], "hints": ["..."]}
```

- **Cite every figure** you use with the source `name`, `url` and `retrieved_at` date.
- **`null` means unknown.** Say "unclear" or "not available". Never fill it with an estimate or a remembered number.
- **Surface `warnings`** where they affect the conclusion, for example "earnings date is an estimate", "latest earnings date already passed" or "sparse ETF data".
- **Units:** fields ending in `_pct` are already in percent. Amounts are in the `currency` field's currency. Prices are usually delayed by `delayed_by_minutes`.
- **Catalysts:** an event with `status: "past"` is not the next date. When there is no upcoming date, say so and point to the company's investor-relations page.
- **`ok: false`:** report the `error` and continue with what you have. If every call fails, switch to Lite Mode.

## 4. What this does not cover

Use web search for these, and cite those sources as well:
- AGM dates
- News, guidance commentary, politics and macro
- Detailed ETF holdings
- German/EU company reports. EDGAR is US only; use the investor-relations page or the Unternehmensregister.

## 5. Lite Mode

- Get figures from web search, preferring primary sources: company IR pages, exchange pages, the issuer's ETF factsheet.
- Mark every such figure as **unverified (web search, not a data fetch)**, with its source and date.
- If no reliable source turns up, say "unclear". Never use a number from memory.
- Store nothing. For the investor's Depot, use a Depot Snapshot if one is attached, otherwise ask in chat.

## Settings

Settings are read from the environment first, then from `<data dir>/.env`. The data dir is `~/.financial-support/`, or `$FINANCIAL_SUPPORT_HOME` if set.

| Setting | Effect |
|---|---|
| `FINNHUB_API_KEY` | Optional. More reliable earnings dates (preferred over Yahoo when set) |
| `SEC_USER_AGENT` | Required for `filings`. SEC requires a contact, e.g. `Jane Doe jane@example.com` |

The `setup` skill writes both. Never ask for these values in the middle of another task; suggest `setup` instead.
