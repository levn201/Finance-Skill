# depot scenarios

Run these in Claude Code and Gemini CLI, with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder.

## 1. Natural-language purchases, mixed currencies

> Ich habe 10 SAP zu 180 € und 5 Apple zu 250 €. Außerdem will ich ASML beobachten.

Expected:
- SAP resolves to `SAP.DE`, Apple to `AAPL` with `--entry-currency EUR`, and ASML is added to the Watchlist
- The skill confirms all three in a short reply
- It offers to record a Thesis

## 2. Show with values

> Wie steht mein Depot?

Expected:
- A table with quantity, entry price, price, value, profit/loss and weight in EUR
- The concentration warning for single stocks, but not for an ETF
- The price source and date
- A short "Warum ist das so?"

## 3. Purchase vs correction, then a snapshot

> Ich hab 2 SAP nachgekauft.

Expected:
- The skill asks for the price, or saves without one and notes that the average entry price is now unknown

> Mach mir einen Snapshot für die Claude-App.

Expected:
- A code block starting with `FINANCIAL-SUPPORT DEPOT SNAPSHOT v1`
- Instructions on where to put it
- A reminder that it is read-only
