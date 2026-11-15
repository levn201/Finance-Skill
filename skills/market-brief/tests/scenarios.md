# market-brief scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that holds a Depot with SAP.DE and AAPL, and ASML.AS on the Watchlist.

## 1. Full brief

> Wie ist die Lage am Markt?

Expected:
- An indicator table from `brief.py data`
- Central banks and the yield curve
- 3–6 themes with sources, including politics/geopolitics
- "Was heißt das für dein Depot?" names the 100 % tech concentration, the USD share via Apple, and themes touching ASML or SAP
- "Warum ist das so?"
- No buy or sell recommendation
- The brief is saved

## 2. Second brief

> Lagebild bitte nochmal.

Expected:
- A "Seit dem letzten Lagebild" section with the VIX then versus now and new or dropped themes

## 3. Political single question

> Was bedeuten neue US-Zölle auf Halbleiter für mich?

Expected:
- The mechanism explained, and the effect on ASML (Watchlist) and Apple (supply chain)
- Sources given
- Nothing saved
