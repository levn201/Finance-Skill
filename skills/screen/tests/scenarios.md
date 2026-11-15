# screen scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that holds a profile and a Depot with SAP.DE.

## 1. Region screen with profile weights

> Such mir interessante deutsche Large Caps.

Expected:
- Screener mode `--region de` with a minimum market cap
- Foreign listings such as Apple on Xetra appear under dropped, not in the results
- A top-10 table, with SAP marked "im Depot"
- The relative nature of the scores is explained
- An offer to run `assess` or add to the Watchlist

## 2. Theme

> Welche europäischen Rüstungsaktien passen zu mir?

Expected:
- Candidates from sources such as ETF holdings or company reports
- A theme fit per candidate with reason and source, passed via `--fit`
- The ranking uses the thematic weight

## 3. Emphasis without changing the profile

> Ich suche Dividendenaktien aus den USA.

Expected:
- Adjusted weights proposed for this Screen only, with the dividend weight raised
- The profile stays unchanged
- `--region us --weights …`
