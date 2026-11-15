# sector scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that holds a Depot with SAP.DE (with a Thesis) and AAPL.

## 1. Overview

> Welche Branchen laufen gerade gut und welche schlecht?

Expected:
- US and Europe tables from `overview`, sorted by performance against the market
- Researched reasons for the top and bottom sectors, with sources
- Where SAP.DE and AAPL sit

## 2. Competition

> Wie steht SAP im Vergleich zur Konkurrenz da?

Expected:
- Uses `SAP.DE` and picks direct competitors (e.g. Oracle, Microsoft, Salesforce, Workday) with reasons
- The comparison table with ranks, strengths and weaknesses
- Market share and moat from web sources; `revenue_share_pct` not called market share
- Currency note on the one-year returns

## 3. Sector in depth

> Wie steht es um die Halbleiterbranche?

Expected:
- The Technology row from `overview`
- `compare` with the largest semiconductor companies (e.g. NVDA, TSM, ASML.AS, AVGO, AMD, INTC)
- Drivers of the sector (AI demand, export controls, cycle)
