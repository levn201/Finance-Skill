---
name: assess
description: Gives a reasoned buy, hold or sell Assessment for one stock or ETF, with a separate short-term and medium-term Outlook, reasons for and against, what would change the view, and a check against the investor's Thesis. Records it in the Journal and says what changed since the last Assessment. Use it when the investor asks "soll ich X kaufen/halten/verkaufen?", "was hältst du von X?", "wie siehst du X?", or wants a view on a Position or Watchlist entry.
---

# assess

The core skill. It forms a clear, honest view the investor can decide on (ADR 0002): a direct answer, never a position size.

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3` (the scripts need Python 3.11+ and their own dependencies):

```bash
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
uv run --script <this skill's directory>/../setup/scripts/investor_profile.py show
uv run --script <this skill's directory>/../depot/scripts/depot.py show
uv run --script <this skill's directory>/../thesis/scripts/thesis.py <command>
```

## 0. Rules

These rules hold for every Assessment:

- **Figures:** every figure comes from market-data or a cited source, with its date. Never use a number from memory. Unknown is "unclear".
- **Balance:** look for evidence against the view as hard as for evidence in favour.
- **Language:** answer in the language the investor writes in. Pitch the "Warum ist das so?" section at the Explanation Depth from the Investor Profile.
- **No sizing:** never give a position size, an amount or a share count to buy or sell. Never phrase the view as a certainty.

## 1. Context

1. Run market-data `status` to get the mode. In Lite Mode, see section 6.
2. Read the Investor Profile: setup's `investor_profile.py show`. You need `default_horizon`, `risk_tolerance` and `explanation_depth`. If there is no profile, use medium-term, medium and beginner, and mention `setup` once.
3. Pick the symbol. If the Instrument is a Position or on the Watchlist (see step 4), use **exactly that symbol** everywhere, e.g. `SAP.DE`, not the US ADR `SAP`. Otherwise resolve it with market-data `resolve` and prefer the home listing. A foreign listing has estimates in another currency from fewer analysts.
4. Find where it stands for the investor:
   - depot's `depot.py show`: is it a Position, on the Watchlist, or neither?
   - thesis's `thesis.py show <SYMBOL>`: is there a Thesis?
5. Load the last Assessment: `journal.py last assessment <SYMBOL>`. Its script is in this skill's `scripts/` directory.

## 2. Gather facts

| Source | What |
|---|---|
| market-data `quote`, `fundamentals` | Price, valuation, growth, margins, debt, dividend, analyst range |
| market-data `history --period 1y`, and `--period 5y` for medium-term context | Trend, volatility, drawdown, position vs SMA200 |
| market-data `catalysts` | The next dated event inside the short-term Horizon |
| Web search, company IR first | Latest results and guidance, news of the last ~3 months, competition, regulation, politics that affect this company |

If the facts conflict, say so and name both sources.

## 3. Judge

**Short-term Outlook** (weeks to ~3 months). Typical drivers:
- upcoming Catalysts
- momentum and volatility
- recent news, competition headlines and sentiment

**Medium-term Outlook** (~6–18 months). Typical drivers:
- growth and margin trend
- valuation versus peers and the company's own history
- competitive position
- whether the Thesis holds

Each Outlook gets a `direction` (`positive`, `neutral`, `negative` or `uncertain`), a one-sentence summary and its drivers. The two may differ, for example: "Im nächsten Jahr hohes Potenzial, kurzfristig aber Schwankungen durch steigende Konkurrenz möglich."

**The Thesis.** If there is one, test each pillar and exit trigger, as in the `thesis` skill's check. A broken Thesis is a strong sell argument for a Position. Offer to save the check with `thesis.py check`.

**The view** is based on `default_horizon`:

| `view` | Position | Watchlist / not held |
|---|---|---|
| `buy` | Nachkaufen | Kaufen |
| `hold` | Halten | Abwarten |
| `sell` | Verkaufen | Nicht kaufen |

Weigh the risks against `risk_tolerance`. A highly volatile stock can be "hold" for a low-risk investor and "buy" for a high-risk one. State that this played a role.

Set `confidence` (`high`, `medium` or `low`) honestly. With thin or conflicting data, use `low`.

## 4. Output

Use this structure, with headings in the investor's language:

1. **Einschätzung:** the view label from the table plus the confidence, in one line. Then 2–3 sentences of core reasoning.
2. **Ausblick:** a two-row table (kurzfristig | mittelfristig) with direction, summary and main drivers.
3. **Dafür / Dagegen:** bullet lists, each point with its figure and source.
4. **These:** a pillar scorecard if a Thesis exists. Otherwise one line offering to record one.
5. **Was die Einschätzung ändern würde:** concrete invalidation points, e.g. "Cloud-Wachstum < 15 %" or "Kurs unter SMA200 nach schwachen Zahlen".
6. **Seit der letzten Einschätzung:** from the journal diff, e.g. "Halten → Verkaufen seit 12.10., weil …". Skip this on the first Assessment.
7. **Warum ist das so?:** the causes in plain words, at the investor's Explanation Depth.
8. **Quellen:** a list with dates. Then one line: "Keine Anlageberatung: eine Einschätzung zur eigenen Entscheidung, kann falsch sein."

## 5. Save to the Journal

**Save before you present.** The save returns the `diff` to the last Assessment, which feeds part 6 of the output. Save one JSON entry with `journal.py save assessment --input <inbox>/assessment.json`. Write the JSON with your file-writing tool to `<inbox>/assessment.json` and pass `--input <that file>`. `<inbox>` is the `inbox` path from market-data `status`. The script deletes the file after a successful save. Don't put JSON in the shell command itself: Claude Code blocks commands that contain `{"`. The entry:

```json
{"subject": "SAP.DE",
 "data": {"symbol": "SAP.DE", "name": "SAP SE", "view": "hold", "context": "position",
          "horizon_basis": "medium-term", "confidence": "medium", "thesis_verdict": "intact",
          "outlooks": {"short-term":  {"direction": "uncertain", "summary": "...", "drivers": ["..."]},
                       "medium-term": {"direction": "positive",  "summary": "...", "drivers": ["..."]}},
          "reasons_for": ["..."], "reasons_against": ["..."], "invalidation": ["..."],
          "key_figures": [{"label": "KGV", "value": 30.9, "source": "Yahoo Finance", "as_of": "2026-11-15"}],
          "sources": [{"name": "...", "url": "...", "retrieved_at": "..."}], "lite_mode": false},
 "report_markdown": "<the full answer, without part 6>"}
```

Field values:
- `context`: `position`, `watchlist` or `other`
- `thesis_verdict`: `intact`, `weakened`, `broken`, `unchecked` or `none` (no Thesis)

The script rejects incomplete Assessments, for example ones missing an Outlook per Horizon, reasons against, invalidation points or sources, or containing position sizes. If it refuses, fix the gap rather than dropping the save.

## 6. Lite Mode

Do the same analysis with figures from web search, marked as unverified (web search, not a data fetch), with source and date.
- Context comes from a Depot Snapshot or the chat.
- There is no Journal, so skip "Seit der letzten Einschätzung" and say that nothing is saved.
