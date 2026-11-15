# depot-review scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that holds:
- a profile
- SAP.DE (with a Thesis and an Assessment from today) and AAPL in the Depot
- ASML.AS on the Watchlist

## 1. First review

> Mach einen Depot-Check.

Expected:
- SAP's Assessment is marked as "übernommen"
- AAPL and ASML get fresh Assessments, saved in the Journal
- A ranked table with labels per group (Depot: Verkaufen/Nachkaufen/Halten, Watchlist: Kaufen/Abwarten/Nicht kaufen)
- A Handlungsbedarf section
- The Depot structure with concentration as a risk, not a sell percentage
- "Warum ist das so?" and sources
- The review is saved

## 2. Second review

> Nochmal, was hat sich seit dem letzten Check geändert?

Expected:
- Almost everything is reused
- A "Seit dem letzten Depot-Check" section from `diff`

## 3. Drill-down

> Warum soll ich Apple halten?

Expected:
- The full Assessment for AAPL from the Journal, or a fresh `assess` run
