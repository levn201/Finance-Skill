---
name: explain
description: Explains financial terms, mechanisms and market events in plain language at the investor's Explanation Depth, using the investor's own Depot as examples. Covers terms ("Was ist ein KGV?", "was bedeutet Ex-Dividende?"), connections ("warum fallen Tech-Aktien, wenn die Zinsen steigen?") and concrete events ("warum fällt SAP trotz guter Zahlen?"). Use it whenever the investor asks what something means or why something happens, or doesn't understand part of another skill's answer.
---

# explain

Helps the investor understand why things are the way they are. Explaining is the goal, never a buy or sell view.

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3` (the scripts need Python 3.11+ and their own dependencies):

```bash
uv run --script <this skill's directory>/../setup/scripts/investor_profile.py show
uv run --script <this skill's directory>/../depot/scripts/depot.py show
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
```

## 1. Context

- **Explanation Depth:** read it from the Investor Profile (setup's `investor_profile.py show`). If there is no profile, use `beginner`.
- **The investor's Instruments:** read them with depot's `depot.py show`, if the Depot can be reached. They are used as examples.

In Lite Mode, use a Depot Snapshot if there is one, otherwise examples of well-known companies.

## 2. Three kinds of questions

| Kind | Example | What you need |
|---|---|---|
| **Term** | "Was ist ein KGV?", "Was heißt Ex-Dividende?" | A standard definition. The example uses live figures |
| **Mechanism** | "Warum fallen Tech-Aktien bei steigenden Zinsen?", "Was macht ein starker Dollar mit meinen US-Aktien?" | The causal chain, step by step |
| **Event** | "Warum fällt SAP trotz guter Zahlen?", "Warum ist der DAX heute gefallen?" | Facts first: market-data for the move (`quote`, `history`), web search for what happened. Then the explanation |

For events, separate what is **confirmed** (reported by the company or a reliable source) from what is **likely** (common explanations from commentary). If the cause is unclear, say so and name the 2–3 most plausible causes with their evidence. Never present a guess as the reason.

## 3. Structure of the answer

In the investor's language:

1. **Kurz gesagt:** the answer in 1–2 sentences.
2. **Erklärung:**
   - **Beginner:** everyday words, one picture or analogy, at most one formula, written out ("Kurs geteilt durch Gewinn pro Aktie"). Every technical term is explained the first time it appears.
   - **Advanced:** precise terms, the formula, typical value ranges and caveats. No analogies needed.
3. **An deinem Depot:** one example with an Instrument from the Depot or Watchlist. Take its real figures from market-data, with source and date, e.g. "SAP hat aktuell ein KGV von 30,9 (Yahoo Finance, 15.11.2026). Du zahlst also rund 31 Jahresgewinne." If there is nothing fitting in the Depot, pick a well-known company and say so.
4. **Worauf achten:** the limits and typical misreadings. For example: a low P/E can mean a company is cheap, or that the market expects falling profits.
5. **Verwandte Begriffe:** 2–3 terms worth looking at next. Offer to explain them.

Keep it short. A term usually needs 8–15 lines, an event explanation a bit more. Offer to go deeper rather than writing everything at once.

## 4. Accuracy

- **Definitions:** use the standard definition. Where definitions differ, say so. For example, the trailing P/E uses the last 12 months of profit, the forward P/E uses expected profit.
- **Figures:** every figure about a real Instrument comes from market-data or a cited source, with its date. Illustrative numbers in an analogy are fine, but they must be recognisable as made up ("angenommen, eine Firma verdient 10 € pro Aktie …").
- **German specifics:** keep the specifics of the investor's situation where they matter, e.g. that the Abgeltungsteuer applies to dividends and gains, or that a German broker may trade US shares in EUR. Don't give tax advice beyond general rules, and point to a tax advisor for individual cases.

## 5. Handing over

- If the question turns into "should I buy or sell?", explain the concept and offer `assess`.
- If it's about the whole market, explain and offer `market-brief`.
