---
name: depot-review
description: Depot Review. Gives an Assessment of every Position and every Watchlist entry in one go, ranked into what to sell, buy more of, hold, buy or wait for, with the Depot's structure (value, profit/loss, concentration), upcoming critical dates and what changed since the last review. Use it when the investor asks "wie steht mein Depot?", "was soll ich kaufen oder verkaufen?", "Depot-Check", "geh mein Depot durch" or wants an overview of all holdings and candidates.
---

# depot-review

The overview the investor decides on. For each Instrument it reuses or makes an Assessment, following the rules of the `assess` skill, and condenses everything into one ranked summary.

```bash
uv run --script <this skill's directory>/scripts/review.py dossier
uv run --script <this skill's directory>/scripts/review.py save < review.json
```

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3` (the scripts need Python 3.11+ and their own dependencies):

```bash
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
uv run --script <this skill's directory>/../setup/scripts/investor_profile.py show
uv run --script <this skill's directory>/../thesis/scripts/thesis.py <command>
uv run --script <this skill's directory>/../assess/scripts/journal.py <command>
```

## 1. Context

1. Run market-data `status`. In Lite Mode, see section 6.
2. Read the Investor Profile: setup's `investor_profile.py show`.
3. Run `review.py dossier`. For every Position and Watchlist entry it returns:
   - `quote`, `key_figures` and `history`
   - `next_events` (upcoming Catalysts)
   - `thesis` (verdict and last check)
   - `last_assessment`
   - `reuse`, a decision whether the last Assessment can be taken over

   It also returns the Depot `valuation` with weights and profit/loss, the `valuation_warnings` (concentration and similar) and `last_review_at`.

If the Depot and Watchlist are empty, say so, point to `depot`, and stop.

## 2. One Assessment per Instrument

**`reuse.reuse` is true** (at most 7 days old, price moved 10 % or less, no results since): take over the last view and confidence, and mark it as "übernommen vom <Datum>". Don't search again.

**Otherwise** make a compact Assessment following the `assess` skill's rules (its sections 0, 2 and 3):
- Start from the dossier figures.
- Add 1–2 targeted web searches: the latest results and guidance, and major news of the last weeks.
- Test the Thesis if there is one.
- Form both Outlooks and the view on the profile's `default_horizon`.
- Save each fresh Assessment with assess's `journal.py save assessment`, so a later `assess` sees it. Its full rules apply: Outlook per Horizon, reasons for and against, invalidation points, sources.

If more than 12 Instruments need a fresh Assessment, tell the investor how many before starting. Offer to do the Positions first.

A data lookup that failed (`warnings` says so) means: assess that Instrument by web search, marked as unverified.

## 3. Save the review

Build the review and pipe it into `review.py save`:

```json
{"summary": "2–3 sentences: overall state and the most important actions",
 "items": [{"symbol": "SAP.DE", "in": "depot", "view": "hold", "confidence": "medium",
            "reason": "one line with the decisive point", "reused": false}],
 "report_markdown": "<the full answer, without the 'Seit dem letzten Depot-Check' part>"}
```

The script checks that every Position and Watchlist entry appears exactly once. It returns the items `ranked` and labelled:
- Depot: Verkaufen, Nachkaufen, Halten
- Watchlist: Kaufen, Abwarten, Nicht kaufen

It also returns the `diff` to the last review. Save before presenting, so the diff is available.

## 4. Output

Present in the investor's language:

1. **Kurzfazit:** the `summary`.
2. **Übersicht:** one table in the ranked order, with these columns:
   - Rang
   - Wert
   - Depot/Watchlist
   - Einschätzung (the label)
   - Konfidenz
   - Ausblick kurz | mittel, as arrows ↑ → ↓ ?
   - Grund (one line)
   - neu/übernommen
3. **Handlungsbedarf:**
   - Positions labelled Verkaufen, or with a weakened or broken Thesis
   - Watchlist entries labelled Kaufen
   - critical dates in the next 14 days from `next_events`

   For each one, give the reason and what would change the view.
4. **Depot-Struktur:**
   - total value and profit/loss in the base currency
   - concentration warnings, the currency mix, and Positions without a Thesis

   Phrase concentration as a risk, never as "sell X %". Never size positions.
5. **Seit dem letzten Depot-Check:** from `diff`, e.g. "SAP: Halten → Verkaufen". Skip this on the first review.
6. **Warum ist das so?:** the 2–3 most important causes behind the overall picture, in plain words at the investor's Explanation Depth.
7. **Quellen** with dates, and the line "Keine Anlageberatung: eine Einschätzung zur eigenen Entscheidung, kann falsch sein."

Offer details on request. For any line the investor asks about ("warum SAP verkaufen?"), show the full Assessment from the Journal, or run `assess`.

## 5. Consistency

- Two Instruments with similar facts should not get opposite views without a stated reason, for example a different Thesis or different risk.
- The overall summary must match the table.

## 6. Lite Mode

- Positions and Watchlist come from a Depot Snapshot or the chat.
- Make every Assessment by web search, with figures marked as unverified, source and date.
- Rank by the order in section 4.
- Nothing is saved, so there is no "Seit dem letzten Depot-Check". Say so.
