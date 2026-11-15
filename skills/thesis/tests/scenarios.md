# thesis scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that already holds a Depot with SAP.DE.

## 1. Record from vague reasons

> Ich hab SAP gekauft, weil das eine gute Firma ist und Cloud boomt.

Expected:
- The skill asks follow-up questions to make the pillars checkable, e.g. "Ab welchem Cloud-Wachstum wärst du zufrieden?"
- It asks for at least one exit trigger
- It shows the draft and saves only after confirmation
- It invents no pillars without marking them as suggestions

## 2. Check

> Stimmt meine SAP-These noch?

Expected:
- A scorecard with the current figures from market-data and web search, each with source and date
- Exit triggers checked
- A verdict of intact, weakened or broken saved with `check`
- A "Warum ist das so?" section
- No buy/sell recommendation, but an offer to run `assess`

## 3. Gaps

> Wo fehlen mir noch Thesen?

Expected:
- `gaps` lists the Positions and Watchlist entries without a Thesis
- The skill offers to record them one by one
