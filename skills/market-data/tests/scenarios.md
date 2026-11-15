# market-data scenarios

Run each prompt in Claude Code and in Gemini CLI. `market-data` is an internal helper, so the prompts exercise it through plain questions.

## 1. German stock by ISIN

> What are the current P/E, dividend yield and next earnings date of DE0007164600?

Expected:
- `status` runs first
- The ISIN resolves to `SAP.DE`, with figures in EUR
- Every figure cites Yahoo Finance with the retrieval date
- If the earnings date has passed, the answer says there is no confirmed upcoming date, rather than presenting the old one

## 2. ETF with sparse data

> How expensive is EUNL.DE and how has it performed this year?

Expected:
- The TER of 0.2 % comes from `fundamentals`, and returns come from `history`
- The answer passes on the sparse-ETF-data warning
- Missing values are called unclear, not estimated

## 3. Lite Mode

Run this in an environment without shell access, such as the Claude app chat:

> What is Apple's current share price?

Expected:
- The price comes from web search
- It is marked as unverified (web search, not a data fetch), with its source and date
- Nothing is written to disk
