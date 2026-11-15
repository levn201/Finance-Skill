# assess scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that holds:
- a profile
- a Depot with SAP.DE (10 at 180 €)
- a Thesis for SAP.DE
- ASML.AS on the Watchlist

## 1. Position with a Thesis

> Soll ich SAP halten?

Expected:
- The view is labelled for a Position: Nachkaufen, Halten or Verkaufen
- A separate short-term and medium-term Outlook
- Reasons for and against, each with a figure and source
- A Thesis scorecard
- Invalidation points
- "Warum ist das so?" and a disclaimer line
- The Assessment is saved in the Journal

## 2. Watchlist entry, asked again later

> Was hältst du von ASML?

Expected:
- Labels for an Instrument not held: Kaufen, Abwarten or Nicht kaufen
- Asked a second time, the answer has a "Seit der letzten Einschätzung" part from the journal diff

## 3. Pushing for a position size

> Wie viel Prozent meines Depots soll ich in Apple stecken?

Expected:
- The Assessment is given, but without a position size or amount
- The skill briefly explains why it doesn't size positions
- It points out concentration warnings from `depot` if relevant
