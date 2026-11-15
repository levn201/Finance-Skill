# explain scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that holds a profile (`explanation_depth: beginner`) and a Depot with SAP.DE and AAPL.

## 1. Term at beginner depth

> Was ist ein KGV?

Expected:
- "Kurz gesagt", then a plain explanation with an analogy and no jargon left unexplained
- An example with SAP's real P/E from market-data, with source and date
- Limits of the measure and related terms

## 2. Event

> Warum ist Apple trotz guter Zahlen gefallen?

Expected:
- The move is taken from market-data and the cause from web search
- Confirmed and likely causes are separated, with sources
- No buy or sell view, but an offer to run `assess`

## 3. Advanced depth

Run `set explanation_depth=advanced` first.

> Was macht ein starker Dollar mit meinem Depot?

Expected:
- A precise mechanism covering the currency translation of USD positions
- The example uses Apple's weight and the EUR/USD rate, with sources
- No basic analogies
