---
name: screen
description: Screen. Finds and ranks stocks by the investor's weighted criteria (fundamentals, valuation, dividend, theme fit, technical trend) from the Investor Profile. The universe is a region/sector (e.g. German large caps, US utilities) or a theme researched by web search (e.g. "KI-Profiteure", "Rüstung Europa", "Dividendenaktien"). Use it when the investor asks "such mir Aktien, die …", "welche Aktien passen zu …", "finde günstige Dividendenwerte", or wants new candidates for the Watchlist.
---

# screen

Turns the investor's criteria into a ranked list of candidates. A Screen finds candidates. It is not an Assessment: the top of the list is where to look closer, not what to buy.

```bash
uv run --script <this skill's directory>/scripts/screen.py --region de [--sector Technology] [--min-mcap 2e9] [--size 60]
uv run --script <this skill's directory>/scripts/screen.py --symbols RHM.DE HAG.DE ... [--fit RHM.DE=95 HAG.DE=90 ...]
```

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3` (the scripts need Python 3.11+ and their own dependencies):

```bash
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
uv run --script <this skill's directory>/../depot/scripts/depot.py show
```

## 1. Understand the request

Work out four things:

- **Universe:** a region (`us`, `de`, `fr`, `nl`, `gb`, `ch`, `it`, `es`, `at`, `be`, `dk`, `fi`, `se`, `no`), optionally a sector, or a theme. If none is given, ask once, suggesting "deutsche und europäische Large Caps".
  - Sectors use Yahoo's names: Technology, Healthcare, Financial Services, Industrials, Consumer Cyclical, Consumer Defensive, Energy, Utilities, Basic Materials, Real Estate, Communication Services.
- **Weights:** these come from the Investor Profile. If the request clearly emphasises one criterion ("Dividendenaktien", "günstig bewertet"), propose adjusted weights for **this Screen only**, e.g. `--weights fundamentals=25 valuation=20 dividend=40 thematic=0 technical=15`.
  - Say that this doesn't change the profile.
  - Weights must add up to 100.
- **Size:** for example a minimum market cap, using `--min-mcap` in the listing currency.
- **ETFs:** the Screen covers stocks only. For ETFs, explain that and offer to compare specific ETFs with market-data instead.

## 2. Build the universe

**Region or sector.** Run the screener mode. The script takes the largest listings on the region's home exchange, keeps companies headquartered in that country, and drops OTC and duplicate listings. `dropped` says why. Add `--any-country` only if the investor wants foreign companies listed there too.

**Theme.**

1. Find 10–40 candidates by web search from solid sources:
   - holdings of thematic ETFs (issuer factsheets)
   - industry reports
   - company reports showing what share of revenue comes from the theme
2. Resolve each candidate to its home listing with market-data `resolve`.
3. Judge the **theme fit** from 0 to 100 per candidate, with a reason and a source:

| Theme fit | Meaning | Example ("Rüstung Europa") |
|---|---|---|
| 80–100 | Pure play: the theme is the core business | Rheinmetall (defence is the main business) |
| 40–79 | A significant segment | Airbus (defence is one segment) |
| 0–39 | Marginal | Siemens (minor defence-related business) |

Base each fit on a source that shows the business mix, for example a segment report or the revenue share named by the company. If you can't find one, keep the value but mark it as your estimate in the output.

Pass the scores as arguments:

```bash
uv run --script …/screen.py --symbols RHM.DE AIR.PA SIE.DE --fit RHM.DE=95 AIR.PA=55 SIE.DE=10
```

Without `--fit`, the thematic weight is spread over the other criteria (the script notes this). For a theme request, always pass `--fit`.

## 3. How scoring works

Explain this briefly in the output:

- **Relative scores:** each metric is ranked against the other candidates on a 0–100 percentile, so a score says "better or worse than the others here", not "cheap in absolute terms". Fewer than 5 candidates make the ranking weak, and the script notes this.
- **What each criterion combines:**

| Criterion | Metrics |
|---|---|
| Fundamentals | Revenue growth, operating margin, return on equity, debt/equity (lower is better) |
| Valuation | Forward P/E, EV/EBITDA, PEG (lower is better; negative values are left out) |
| Dividend | Yield, and a healthy payout ratio (30–70 % is best, above 90 % is penalised) |
| Technical | 6-month and 1-year return, price above or below the 200-day average |
| Thematic | Your judged theme fit |

- **Banks and insurers:** leverage and EV/EBITDA are skipped for them, because those figures aren't comparable to other companies.
- **Missing data** lowers `coverage_pct` and is never estimated. Treat candidates under 70 % coverage with caution.

## 4. Output

Present in the investor's language:

1. **Was ich gesucht habe:** universe, weights used, and how many candidates were kept or dropped (with the main reasons).
2. **Top 10:** a table with these columns:
   - Rang
   - Wert
   - Score
   - Fundamental
   - Bewertung
   - Dividende
   - Thema (if used)
   - Technik
   - Abdeckung
   - Hinweis: "im Depot", "auf der Watchlist" or empty
3. **Die Top 3–5 kurz erklärt:** per candidate 1–2 sentences on what drives its score, with the underlying figures (from `metrics`) and the source. For a theme, also give the theme-fit reason and its source.
4. **Warum ist das so?:** what the ranking says and what it doesn't, at the investor's Explanation Depth. For example: a high valuation score only means cheaper than these peers. A cheap stock can be cheap for a reason.
5. **Nächste Schritte:** offer `assess` for the most interesting candidates, and to add any to the Watchlist with the `depot` skill. Ask before adding.
6. **Quellen** with dates.

Never present a Screen result as a buy recommendation.

## 5. Lite Mode

- Build the universe by web search.
- Collect the key figures per candidate by web search, marked as unverified (web search, not a data fetch), with source and date.
- Rank qualitatively along the same criteria, without pretend-precise scores.
- Say that nothing is saved and that the ranking is less reliable.
