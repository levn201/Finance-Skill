# valuation scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that holds a Depot with SAP.DE (with a Thesis) and AAPL.

## 1. EUR stock with peers

> Ist SAP aktuell teuer? Was wäre ein fairer Wert?

Expected:
- Uses `SAP.DE` from the Depot
- Looks up the 10-year Bund yield by web search and passes it with `--risk-free`, cited
- Picks software peers (e.g. Oracle, Microsoft, Salesforce, Workday) and says why
- DCF range plus price, reverse DCF, multiples table, top drivers
- No buy or sell view; offers `assess`

## 2. USD stock, reverse DCF focus

> Welches Wachstum preist der Apple-Kurs ein?

Expected:
- Risk-free from `^TNX`, no `--risk-free` needed
- The implied growth compared with Apple's own growth history and guidance
- The drivers explained in plain words

## 3. Bank

> Was ist die Deutsche Bank wert?

Expected:
- The DCF is reported as not applicable, with the reason
- P/B and P/E against European bank peers
