# daily scenarios

Run these in Claude Code with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder that holds a Depot with SAP.DE (with a Thesis), AAPL and ASML.AS on the Watchlist, and an Investor Profile with `language: de`.

## 1. Weekday morning, no review due

> Read skills/daily/SKILL.md and follow it exactly.

Expected (on a weekday, last Depot Review under 7 days old, no big moves):
- `plan`, then Catalysts and Market Brief saved to the Journal; no Depot Review
- A short German Daily Report and `journal/<date>/daily.md`
- First line of the reply: the headline, at most 200 characters
- No change to depot.json, theses.json or profile.json; no files outside the Journal

## 2. Second run the same day

The same prompt again.

Expected: one line ("Kein Tageslauf: already ran today"), nothing saved.

## 3. Manual run on a weekend

> Mach den Tageslauf jetzt.

Expected: `plan --force`, a full run, the report notes the forced run.
