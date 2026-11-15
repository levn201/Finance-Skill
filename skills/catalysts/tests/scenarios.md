# catalysts scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that holds a Depot with SAP.DE and AAPL, and ASML.AS on the Watchlist.

## 1. Overview

> Was steht in den nächsten Wochen an?

Expected:
- The ECB (and Fed, because AAPL is held) meeting dates come from web search with sources
- SAP's and ASML's next earnings dates come from their IR pages, because the data has none
- Critical events (14 days or less) come first, with "why it matters"
- A table of the rest
- The calendar is saved in the Journal

## 2. Second run

> Und jetzt nochmal, was hat sich geändert?

Expected:
- A "Seit dem letzten Mal" section from `diff`, for example no changes or a moved date

## 3. Single question

> Wann kommen die nächsten Zahlen von Apple?

Expected:
- The skill runs only for AAPL with `--symbol AAPL` and doesn't save
- A brief answer that says whether the date is estimated and gives its source
