---
name: daily
description: The unattended daily run. On weekday mornings it updates the Catalysts, writes a Market Brief, runs a Depot Review when one is due (Mondays, after results of a holding, after a big move), and condenses it all into a short Daily Report with what changed since yesterday, saved to the Journal, ending with a one-line headline for the phone notification. Use it when a scheduled task starts it, or when the investor says "mach den Tageslauf", "daily run" or "Tagesbericht".
---

# daily

Runs without the investor watching. Nobody answers questions, so never ask any: decide with the rules below and say in the report what you assumed.

```bash
uv run --script <this skill's directory>/scripts/daily.py plan [--force]
uv run --script <this skill's directory>/scripts/daily.py save --input <inbox>/daily.json
```

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3`:

```bash
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
uv run --script <this skill's directory>/../catalysts/scripts/upcoming.py --save --input <inbox>/catalysts.json
uv run --script <this skill's directory>/../market-brief/scripts/brief.py <data|save>
uv run --script <this skill's directory>/../depot-review/scripts/review.py <dossier|save>
uv run --script <this skill's directory>/../thesis/scripts/thesis.py <command>
uv run --script <this skill's directory>/../assess/scripts/journal.py <command>
```

## 0. Rules for the unattended run

- **Read-only on the investor's data:** never change the Depot, Theses or Investor Profile. Only the save commands above write, and only into the Journal.
- **Files only in the inbox:** write each JSON with your file-writing tool to `<inbox>/<name>.json` (`inbox` from `plan`) and pass it with `--input`. The scripts delete it after saving. Never write anywhere else, and never put JSON in a shell command: Claude Code blocks commands that contain `{"`, and nobody is there to approve them.
- **Language:** write everything in `language` from `plan` (the Investor Profile default), not in the language of the task prompt.
- **No questions:** where a skill would ask the investor, take the default and note it under "Annahmen".
- **Every other rule still holds:** figures with source and date, unknown is "unclear", no position sizes.

## 1. Plan

Run `daily.py plan`. Add `--force` only when the investor started the run by hand.

- **`run: false`** (weekend, or already ran today): reply with one line, e.g. "Kein Tageslauf: Wochenende", and stop. No notification.
- **`late_run: true`:** this is a catch-up after the computer slept. Do the run, and start the report with "Nachgeholter Lauf von <now_local>".
- **`profile_missing`:** run with the defaults and recommend `setup` in the report.

## 2. Catalysts

Follow the `catalysts` skill, sections 2 and 3, without presenting anything yet:
1. Look up the extra events by web search: ECB and Fed meetings, AGMs and confirmed earnings dates.
2. Write them to `<inbox>/catalysts.json` and run `upcoming.py --save --input <inbox>/catalysts.json`.
3. Keep `calendar.events` and the returned `diff`.

## 3. Market Brief

Follow the `market-brief` skill, sections 1 to 3: run `brief.py data`, research the themes, judge them, and save with `brief.py save --input <inbox>/market-brief.json`. Keep the `regime`, the themes and the returned `diff`.

## 4. Depot Review, only if due

If `depot_review_due` is true, follow the `depot-review` skill and save it with `review.py save --input <inbox>/depot-review.json`. It reuses recent Assessments, so only the Instruments that need it get a fresh one. Name the `depot_review_reasons` in the report.

If it is not due, give no new buy or sell views. Mention the latest Depot Review's verdicts only if a Catalyst or a theme touches them.

## 5. The Daily Report

Write it in `language`, short enough to read on a phone in a minute:

1. **Kurz gesagt:** 2–3 sentences.
2. **Seit gestern:** only what changed, from the three diffs: new or moved dates, a new market regime, new or dropped themes, changed buy or sell views, Theses that weakened. On a quiet day write "Keine wesentlichen Änderungen".
3. **Termine:** the next 14 days, with the critical ones marked.
4. **Handlungsbedarf:** what the investor should look at today, or "Nichts Dringendes".
5. **Warum ist das so?:** 2–4 plain sentences on today's most important point, at `explanation_depth`.
6. **Annahmen**, only if any.
7. **Quellen:** the key ones with dates, plus the paths of the full reports saved today.
8. "Keine Anlageberatung: eine Einschätzung zur eigenen Entscheidung, kann falsch sein."

Write it to `<inbox>/daily.json` and save it with `daily.py save --input <inbox>/daily.json`:

```json
{"headline": "<one line, max 200 characters, leading with what to act on>",
 "language": "de", "regime": "normal",
 "changes": ["ASML: Termin bestätigt, 21.01."], "upcoming": [{"date": "2026-11-17", "symbol": "NVDA", "event": "Quartalszahlen"}],
 "actions": ["SAP: Halten → Verkaufen prüfen, These geschwächt"],
 "depot_review": {"ran": true, "reasons": ["Monday"]},
 "report_markdown": "<the full Daily Report>"}
```

`headline` examples: "Ruhiger Tag. Nächster Termin: Nvidia-Zahlen am 17.11." or "ASML −6 %: Depot-Check sagt jetzt Abwarten statt Kaufen, These prüfen". The script rejects a headline over 200 characters. It returns `report_file`, a Markdown copy of the report to open.

## 6. Notify

1. If a `PushNotification` tool is available, send the `headline` as the message.
2. End your reply with the headline as the **first line**, then the full Daily Report. The Claude app shows the finished scheduled task on the phone with this reply.
