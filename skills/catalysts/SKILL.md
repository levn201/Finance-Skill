---
name: catalysts
description: Lists upcoming Catalysts for the investor's Depot and Watchlist (quarterly results, ex-dividend dates, AGMs, plus ECB and Fed meetings) sorted by date. Flags the critical ones in the next two weeks, explains why they matter, and says what changed since the last run. Use it when the investor asks "was steht an?", "welche Termine kommen?", "wann kommen die Zahlen von X?", wants a weekly outlook, or before deciding on a Position.
---

# catalysts

Answers "what's coming, and why should I care?" for everything the investor holds or watches.

```bash
uv run --script <this skill's directory>/scripts/upcoming.py [--days 90] [--symbol X ...] [--save] < extra.json
```

The script reads the Depot and Watchlist itself. It returns `calendar.events` sorted by date, each with `in_days`, `critical` (14 days or less), `estimated` and `source`, plus `no_upcoming_earnings`, `warnings` and `sources`. With `--save` it also returns `diff` against the last saved calendar.

## 1. Mode

Check the mode with market-data `status`. In Lite Mode, see section 5.

## 2. Collect what the data sources don't have

Before the run, use web search for these, preferring primary sources:

| What | Where to look | Example `extra` entry |
|---|---|---|
| ECB monetary-policy meetings | ecb.europa.eu | `{"date":"2026-12-17","type":"central_bank","symbol":null,"title":"EZB-Zinsentscheid","source":"European Central Bank","url":"https://www.ecb.europa.eu/…"}` |
| Fed FOMC meetings (when the investor holds US stocks) | federalreserve.gov | `{"date":"…","type":"central_bank","symbol":null,"title":"Fed-Zinsentscheid (FOMC)","source":"Federal Reserve","url":"…"}` |
| AGMs of Positions, only if likely within the window (German AGMs are mostly April–June) | company IR page | `{"date":"…","type":"agm","symbol":"SAP.DE","title":"SAP Hauptversammlung","source":"SAP Investor Relations","url":"…"}` |
| Earnings dates of Instruments without an upcoming date in the data. Run `upcoming.py` once without `--save` to see which. | company IR financial calendar | `{"date":"2027-01-28","type":"earnings","symbol":"SAP.DE","title":"Q4/FY 2026","source":"SAP Investor Relations","url":"…"}` |

Add only dates you found in a source. If the source only says "late January", leave the event out and mention it in the text instead. Set `"estimated": true` when the source itself calls the date preliminary.

Then run the calendar with the extras on stdin, saving it:

```bash
printf '%s' '[…extra events…]' | uv run --script …/upcoming.py --save
```

## 3. Output

Present in the investor's language:

1. **Kritisch in den nächsten 14 Tagen:** one block per critical event. Give the date, the Instrument (marked as Depot or Watchlist) and the event. Then **why it matters**, in 1–2 sentences.
   - For earnings: what the market expects (the EPS estimate if there is one), and which Thesis pillar it tests.
   - For central banks: how a rate decision tends to affect this Depot, for example growth stocks versus dividend stocks.
2. **Weitere Termine:** a table with Datum | Wert | Termin | Quelle. Mark estimated dates with "(geschätzt)".
3. **Ohne bekannten Termin:** the Instruments in `no_upcoming_earnings` that you couldn't resolve by web search either, with a pointer to their IR page.
4. **Seit dem letzten Mal:** from `diff`: new events, moved dates (e.g. "Apple: 28.01. → 29.01.") and removed ones. Skip this on the first run.
5. **Warum ist das so?:** a short plain-language note at the investor's Explanation Depth, e.g. why prices often move strongly around results, or why rate decisions matter for valuations.
6. **Quellen:** the sources with dates.

Pass on the relevant `warnings`, but don't list every "no ex-dividend date announced" line individually. Summarise them in one sentence.

If the investor asks about a single Instrument ("wann kommen die Zahlen von SAP?"), run with `--symbol SAP.DE`, don't save, and answer briefly.

## 4. Follow-ups

- **Critical earnings date for a Position with a Thesis:** offer an `assess` or `thesis` check before the date.
- **The `earnings` skill:** once it exists, offer an earnings preview for critical results.

## 5. Lite Mode

- Find the dates by web search for each Instrument from the Depot Snapshot or the chat, plus the ECB and Fed.
- Mark the dates as unverified (web search, not a data fetch), with source and date.
- Nothing is saved, so there is no "Seit dem letzten Mal". Say so.
