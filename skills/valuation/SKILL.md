---
name: valuation
description: Estimates what one stock is worth: a simple DCF (discounted free cash flow) with stated assumptions and a fair-value range, a reverse DCF (what growth the current price implies), and a comparison of P/E, EV/EBITDA and other multiples with listed peers. Explains which assumptions drive the result. Use it when the investor asks "ist X teuer?", "was ist SAP wert?", "fairer Wert von X", "ist X über- oder unterbewertet?", or wants a DCF or peer comparison.
---

# valuation

Estimates a Fair Value range for one stock and shows how much it depends on the assumptions. The result is a range, never a price target, and no buy or sell view: offer `assess` for that.

```bash
uv run --script <this skill's directory>/scripts/valuation.py <SYMBOL> [--risk-free 0.027] [--peers A B C ...] \
    [--growth 0.08] [--terminal 0.02] [--erp 0.05] [--discount 0.09] [--base-fcf avg3|latest] [--base-fcf-value N]
```

All rates are fractions (`0.027` = 2.7 %).

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3`:

```bash
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
uv run --script <this skill's directory>/../setup/scripts/investor_profile.py show
uv run --script <this skill's directory>/../depot/scripts/depot.py show
uv run --script <this skill's directory>/../thesis/scripts/thesis.py show <SYMBOL>
```

## 1. Prepare

1. **Symbol:** run `depot.py show`. If the stock is a Position or on the Watchlist, use exactly that symbol, e.g. `SAP.DE`, not the US ADR `SAP`. Otherwise use the home listing (market-data `resolve`).
2. **Risk-free rate:** the 10-year government bond yield of the company's reporting currency. For USD the script reads `^TNX` itself. For anything else, find the current yield by web search (e.g. "Rendite 10-jährige Bundesanleihe" for EUR, Gilts for GBP, Swiss Confederation for CHF) and pass it with `--risk-free`, citing source and date. If you run without it, the script tells you to. Skip this for banks, insurers and ETFs: there the DCF doesn't apply.
3. **Peers:** find 4–8 listed competitors with a similar business by web search, and pass their Yahoo symbols with `--peers`. Prefer companies of similar size and business model over loose sector neighbours. Say why you picked them.

## 2. Run and check

Run `valuation.py`. The result:

| Field | Contents |
|---|---|
| `dcf.assumptions` | Starting free cash flow (default: average of the last 3 years), growth years 1–5 and its source, the fade to terminal growth over years 6–10, discount rate (CAPM: risk-free + beta × equity risk premium), shares, currency factor |
| `dcf.fair_value` | `low` / `base` / `high` per share in the quote currency. Range = growth ±5 points × discount rate ±1 point |
| `dcf.upside_pct` | Base value versus the current price |
| `dcf.drivers` | How much each assumption moves the value, largest first |
| `dcf.sensitivity` | Value grid: discount rate × terminal growth |
| `dcf.implied_growth_years_1_5` | Reverse DCF: the growth the current price implies |
| `dcf.terminal_share_pct` | Share of the value from beyond year 10 |
| `peers` | Each multiple for the target versus the peer median, the premium or discount, and the price the median would imply |
| `dcf.applicable: false` | With a `reason`: banks, insurers, ETFs, negative free cash flow. Then rely on peers |
| `peers.return_on_equity` | Banks and insurers only: return on equity of the target and peers. A higher one justifies a higher P/B |

**Check the growth assumption.** The default comes from analyst estimates (long-term growth, else next year's EPS growth), which is only a proxy for free cash flow growth. If the company's guidance or its revenue trend points elsewhere, rerun with `--growth` and say why. If the starting free cash flow is distorted by a one-off (a large tax payment, a restructuring), use `--base-fcf latest` or `--base-fcf-value` and name the one-off.

## 3. Output

In the investor's language:

1. **Kurz gesagt:** 2–3 sentences, e.g. "Nach DCF zwischen 150 und 240 €, Basisfall 190 € (Kurs 210 €). Der Kurs preist rund 12 % Wachstum pro Jahr ein. Gegenüber Konkurrenten mit KGV-Aufschlag von 20 %."
2. **Annahmen:** a table of every assumption with its value and source. Mark which ones are conventions (terminal growth 2 %, equity risk premium 5 %) and which come from data.
3. **Fairer Wert (DCF):** low / base / high versus the price. Then the sensitivity grid as a small table.
4. **Was der Kurs einpreist:** the reverse DCF. Compare the implied growth with the company's own history and guidance: is it plausible?
5. **Vergleich mit Konkurrenten:** the multiples table with the peers named. Explain a premium or discount: higher growth, margins or quality can justify a premium.
6. **Worauf es ankommt:** the top drivers, in words. For example: "±5 Punkte Wachstum verschieben den Wert um ±25 %, der Zinssatz um ±13 %." If `terminal_share_pct` is high, say that most of the value lies far in the future.
7. **Warum ist das so?:** at the investor's Explanation Depth, what a DCF is and why a small change in growth or interest rate moves it so much. For a beginner: "Eine Aktie ist so viel wert wie das Geld, das das Unternehmen in Zukunft verdient, heruntergerechnet auf heute."
8. **Quellen** with dates, then: "Keine Anlageberatung: Bewertungen hängen stark von Annahmen ab und können falsch sein."

## 4. Rules

- **No false precision:** lead with the range, round to whole currency units, and never call the base case "the" value.
- **Stated assumptions:** every figure has a source and date. A convention is labelled as one. Unknown is "unclear".
- **Pass on warnings,** especially stock-based pay that flatters free cash flow and a high terminal share.
- **Not applicable:** for banks, insurers and ETFs, explain why a DCF doesn't fit and use the peer multiples (P/B and P/E for financials).

## 5. Lite Mode

Without the script, do the peer comparison by web search: the target's and 4–6 peers' P/E, EV/EBITDA and P/B, each marked unverified (web search, not a data fetch), with source and date. Skip the DCF calculation, or give only a rough reverse-DCF explanation in words, and say so.

## Support hint

End your first answer in a conversation with this line, in the investor's language, unless `support` already ran in it:

> Nicht sicher, welcher Skill passt? Frag „Was kannst du?“ oder ruf `/financial-support:support` auf.

In Lite Mode, leave out the command.
