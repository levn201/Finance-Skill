# support scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder.

## 1. Empty start

Empty data folder.

> Was kannst du?

Expected:
- The overview table with every skill except `market-data`, each with an example sentence
- Status line: no profile, empty Depot
- Offers the Startdurchgang, starting with `setup`

## 2. Startdurchgang with a profile and a Depot

A profile and a Depot with SAP.DE and AAPL, no Theses.

> Mach einen Startdurchgang

Expected:
- Says that `setup` and `depot` are already done and skips them
- Starts with `thesis` for SAP.DE and AAPL after asking
- After each step names the next one and asks again; ends with a two-line summary

## 3. Concrete need

> Ich weiß nicht, welchen Skill ich brauche: ich will wissen, ob Nvidia gerade teuer ist

Expected:
- No full table; names `valuation` (and at most one alternative such as `assess`) with an example sentence
- Offers to start it and gives no view of its own

## 4. Hint in another skill

> Was ist ein KGV?

Expected:
- `explain` answers and its first answer ends with the support hint line
