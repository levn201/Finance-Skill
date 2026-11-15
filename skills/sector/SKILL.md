---
name: sector
description: Sector overview and competition. Shows which sectors lead or lag the market in the US and Europe and why, what drives a sector, who the main players are, and how one company stands against its competitors (growth, margins, debt, valuation, share of the group's revenue, market position). Use it when the investor asks "wie läuft die Halbleiterbranche?", "welche Branchen sind gerade stark?", "wer sind die Konkurrenten von SAP?", "wie steht X im Vergleich zur Konkurrenz da?".
---

# sector

Two questions: how a sector is doing and why, and where one company stands within it.

```bash
uv run --script <this skill's directory>/scripts/sector.py overview [--region us|europe|both]
uv run --script <this skill's directory>/scripts/sector.py compare <SYMBOL> --peers A B C ...
```

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3`:

```bash
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
uv run --script <this skill's directory>/../setup/scripts/investor_profile.py show
uv run --script <this skill's directory>/../depot/scripts/depot.py show
```

## 1. Pick the mode

- **Overview:** "Welche Branchen laufen?", or a question about one sector without a company. Run `overview`.
- **Competition:** a question about one company and its competitors. Run `compare`. If the company is a Position or on the Watchlist (`depot.py show`), use exactly that symbol, e.g. `SAP.DE`, not the US ADR `SAP`.
- **One sector in depth** ("Wie steht es um die Halbleiterbranche?"): take its row from `overview`, then run `compare` with the sector's 5–8 largest players, using the biggest one as the symbol.

## 2. Overview

`overview` returns for each sector ETF (US Select Sector SPDRs, iShares STOXX Europe 600 sector ETFs) the 1-month, 3-month and 1-year return and the difference from the market in points (`vs_market_*_pts`, against the S&P 500 or STOXX Europe 600), sorted by the 3-month difference. It also says whether the ETF is above its 200-day line.

Then explain **why** the leaders lead and the laggards lag, by web search from the last 1–3 months:
- interest rates and the economy (e.g. falling rates help real estate and utilities, a weak economy hurts industrials)
- commodity prices (energy, basic resources)
- politics and regulation: tariffs, subsidies, defence budgets, drug pricing
- sector-specific news: an AI investment cycle, a car-market slump

Separate confirmed points from interpretation, and name which of the investor's Positions sit in the strongest and weakest sectors (`depot.py show`, sector from market-data `fundamentals`).

## 3. Competition

1. **Find the competitors** by web search: 4–8 listed companies with an overlapping business. Prefer direct competitors named in the company's annual report or by analysts over loose sector neighbours. Resolve each with market-data `resolve` (home listing).
2. **Run `compare`.** It returns:

| Field | Contents |
|---|---|
| `companies` | Name, country, industry, market cap, revenue in USD |
| `comparison.table` | Every metric per company, plus `revenue_share_pct`: the share of **this group's** combined revenue, not market share |
| `comparison.summary` | For each metric: the target's value, the group median and its rank (1 = best) |
| `comparison.strengths` / `weaknesses` | Metrics where the target ranks in the top or bottom third |
| `sector_performance` | The company's sector ETF against the market |

3. **Add what the numbers don't show,** by web search, each point with source and date:
   - real **market share** in the relevant segment, from industry reports (IDC, Gartner, company reports)
   - **moat:** switching costs, network effects, scale, patents, brand
   - **threats:** new competitors, technology shifts, price pressure, regulation
   - recent moves: big contracts won or lost, acquisitions, price changes

## 4. Output

In the investor's language.

**Overview:**
1. **Kurz gesagt:** the leading and lagging sectors in 2–3 sentences.
2. **Tabelle:** sector, 3 months, versus the market, 1 year. US and Europe separately.
3. **Warum:** the drivers behind the top 3 and bottom 3.
4. **Dein Depot:** which Positions sit where.
5. **Warum ist das so?:** why sectors move in turn, at the investor's Explanation Depth.
6. **Quellen** with dates.

**Competition:**
1. **Kurz gesagt:** the company's position in 2–3 sentences, e.g. "SAP wächst langsamer als ServiceNow, ist aber profitabler und kaum verschuldet."
2. **Wer sind die Konkurrenten:** each in one line, with why it competes.
3. **Vergleich:** a table of the key metrics, with the target's rank.
4. **Stärken / Schwächen:** from the ranks plus the moat and threats found.
5. **Branche:** how the sector is doing against the market.
6. **Warum ist das so?:** what makes a company win in this industry, at the investor's Explanation Depth.
7. **Quellen** with dates.

No buy or sell view: offer `assess` for a single company and `valuation` for whether it is expensive.

## 5. Rules

- **Figures:** every figure needs a source and date. Unknown is "unclear".
- **Market share:** `revenue_share_pct` describes the chosen group only. Never call it market share.
- **Currencies:** one-year returns are in each listing's own currency, so exchange-rate moves are part of them. Say so when you compare EUR and USD stocks.
- **Banks:** for banks, margins and debt are left out because they mean something else. Compare P/E, P/B, ROE and dividend.

## 6. Lite Mode

Use web search for sector performance (index or ETF returns from issuer or exchange pages) and for the competitors' key figures, each marked unverified (web search, not a data fetch), with source and date. Keep the comparison to 3–5 metrics you could verify.
