---
name: support
description: The help desk for the financial-support skills. Lists every skill with a one-line explanation and an example sentence, shows where the investor stands (profile, Depot, Theses), runs a guided Startdurchgang through setup, depot, thesis and the first Depot Review, and points to the one skill that fits a need. Use it when the investor asks "was kannst du?", "Hilfe", "welcher Skill passt?", "ich weiß nicht weiter", "wo fange ich an?", or is starting out.
---

# support

The investor's way in. Show what the skills can do, find out where the investor stands, and hand over to the skill that fits. Every buy, sell or hold view, every figure and every change belongs to the skill you hand over to.

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3` (the scripts need Python 3.11+ and their own dependencies):

```bash
uv run --script <this skill's directory>/../setup/scripts/investor_profile.py show
uv run --script <this skill's directory>/../depot/scripts/depot.py show
uv run --script <this skill's directory>/../thesis/scripts/thesis.py gaps
```

## 1. Where the investor stands

Run the three commands above. Read from them:

| Check | Done when |
|---|---|
| Investor Profile | `profile` is not `null` |
| Depot | `depot.positions` or `depot.watchlist` is not empty |
| Theses | `gaps.missing` is empty |

If a command can't run, you are in **Lite Mode** (section 5).

## 2. The overview

Answer in the investor's language. Start with one sentence on what the skills are: a research assistant for the investor's own Depot, never investment advice. Then show this table, with the example sentences in the investor's language:

| Wofür | Skill | Was er macht | So fragst du |
|---|---|---|---|
| Start | `setup` | Investor Profile: Erklärtiefe, Horizont, Risiko, Screening-Gewichte | „Richte mich ein“ |
| Depot | `depot` | Merkt sich Positionen und Watchlist, zeigt Wert und G/V | „Ich habe 10 SAP zu 180 € gekauft“, „Zeig mein Depot“ |
| Depot | `thesis` | Hält fest, warum du eine Aktie hältst, und prüft, ob das noch stimmt | „Stimmt meine These zu ASML noch?“ |
| Depot | `depot-review` | Geht alle Positionen und die Watchlist durch: verkaufen, nachkaufen, halten, kaufen | „Geh mein Depot durch“ |
| Eine Aktie | `assess` | Kaufen, halten oder verkaufen, kurz- und mittelfristig | „Soll ich Nvidia kaufen?“ |
| Eine Aktie | `valuation` | Fairer Wert per DCF und Vergleich mit Konkurrenten | „Ist SAP teuer?“ |
| Eine Aktie | `earnings` | Quartalszahlen: was erwartet wird, was kam, warum der Kurs reagiert | „Was wird von den Apple-Zahlen erwartet?“ |
| Markt | `catalysts` | Termine: Zahlen, Dividenden, Hauptversammlungen, EZB und Fed | „Was steht diese Woche an?“ |
| Markt | `market-brief` | Lagebild: Indizes, Zinsen, Politik und was das für dein Depot heißt | „Wie ist die Lage am Markt?“ |
| Markt | `sector` | Welche Branchen laufen, wer gegen wen steht | „Wer sind die Konkurrenten von SAP?“ |
| Neue Ideen | `screen` | Sucht Aktien nach deinen Kriterien | „Such mir günstige Dividendenaktien“ |
| Verstehen | `explain` | Erklärt Begriffe und Zusammenhänge an deinem Depot | „Was ist ein KGV?“ |
| Automatisch | `daily` | Tageslauf an Werktagen mit kurzem Bericht aufs Handy | „Mach den Tageslauf“ |

Below the table:
- **How to call a skill:** just write the question. Claude picks the skill. In Claude Code, `/financial-support:<skill>` calls one directly.
- **Where the investor stands:** one line per check from section 1, e.g. "Profil ✓ · Depot: 4 Positionen, 2 auf der Watchlist · Thesen: 6 fehlen".
- **Offer:** if any check is not done, offer the Startdurchgang (section 3) and name its next step. If all are done, ask what the investor wants to do.

If the investor came with a concrete need ("ich will wissen, ob ich Nvidia kaufen soll"), skip the table: name the one skill that fits, with its example sentence, and offer to start it.

## 3. The Startdurchgang

A guided tour in this order. Skip every step whose check from section 1 is done, and say so in one line ("Profil hast du schon").

1. **`setup`**: create the Investor Profile.
2. **`depot`**: enter Positions and the Watchlist.
3. **`thesis`**: record a Thesis for each entry in `gaps.missing`. The investor may skip any of them.
4. **`depot-review`**: the first Depot Review.
5. **`catalysts`**: the dates of the next weeks.
6. **`daily`**: explain that the daily run is a scheduled task in the Claude desktop app, and point to the "Daily run" section of the plugin's README for the setup. Setting it up is the investor's own step.

For each step:
- Say in one sentence what it does and why it comes now, then ask whether to start it.
- On yes, follow that skill's `SKILL.md` until it is finished.
- Then name the next step and ask again.

The Startdurchgang is done when every step is finished, skipped by its check, or declined by the investor. Close with a two-line summary of what is now set up and which question to try next.

## 4. Pointing to a skill

When the investor's need fits several skills, name the best fit first and at most one alternative, each with its example sentence. Questions about this assistant itself (where the data lives, Lite Mode, the app bundle) are answered from the plugin's README.

## 5. Lite Mode

- Without the scripts, skip section 1. Ask whether the investor has a Depot Snapshot (a block starting with `FINANCIAL-SUPPORT DEPOT SNAPSHOT v1`) and read the Depot from it if so.
- Show the overview without `daily` and without the `/financial-support:<skill>` line. Say once that nothing is saved here and that the full edition runs in Claude Code and the Gemini CLI.
- In the Startdurchgang, `setup` and `depot` only apply to this conversation. Skip step 6.
