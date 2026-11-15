---
name: thesis
description: Records and checks the investor's Thesis, the reason they hold or watch an Instrument, as a short statement, 1–5 pillars and exit triggers. Logs new data points against it and tests whether it is still intact, weakened or broken. Use it when the investor explains why they bought or watch something, asks "is my thesis still intact?" / "stimmt meine These noch?", reports news about a holding, or when a Position or Watchlist entry has no Thesis yet.
---

# thesis

A Thesis is the **investor's** reason for holding or watching an Instrument, written so that it can be proven wrong. The `assess` skill later tests buy, hold or sell views against it.

A good sell reason is usually "the Thesis is broken", not "the price fell". This skill makes that check possible.

```bash
uv run --script <this skill's directory>/scripts/thesis.py <command>
```

Every command prints JSON with `ok` and `error`. The data lives in `<data dir>/theses.json`. If the script can't run, see section 6.

## 1. Recording a Thesis

**1. Ask why.** Ask why the investor bought or watches the Instrument, in their own words.

**2. Draft it.** From the answer, draft:

| Part | What it is | Example |
|---|---|---|
| Statement | One sentence | "SAP wird durch den Umstieg auf Cloud profitabler." |
| Pillars | 1–5, each concrete and checkable, with numbers where possible | "Cloud-Umsatz wächst > 20 % pro Jahr" |
| Exit triggers | At least 1: what would prove the Thesis wrong | "Cloud-Wachstum zwei Quartale in Folge unter 15 %" |
| Horizon | `short-term` or `medium-term` | Default from the Investor Profile |
| Conviction | `high`, `medium` or `low` | `medium` |

Help the investor sharpen vague reasons. For example, turn "gute Firma" into "Marge über 25 %" by asking. Never invent reasons the investor didn't give. If you suggest a pillar, mark it as a suggestion and let them accept or drop it.

**3. Confirm and save.** Show the draft and ask for confirmation. Then save it:

```bash
... thesis.py record SAP.DE --name "SAP SE" --statement "..." --pillar "..." --pillar "..." --exit-trigger "..."
```

The symbol must match the one in the Depot or Watchlist (see the `depot` skill).

## 2. Logging a data point

When the investor reports news ("SAP hat 27 % Cloud-Wachstum gemeldet"), log it. Note which pillar it strengthens or weakens, with a source if you checked it:

```bash
... thesis.py log SAP.DE --text "Q3: Cloud-Umsatz +27 %" --impact 1=strengthens --source <url> --date 2026-10-21
```

## 3. Checking a Thesis

1. **Load it:** `show SAP.DE`.
2. **Gather current facts** for each pillar and exit trigger:
   - figures from market-data (`fundamentals`, `history`, `catalysts`)
   - news and latest results from web search (company IR first)
   - Every fact needs a source and date. "Unclear" is a valid finding.
3. **Look for disconfirming evidence** as hard as for confirming evidence.
4. **Judge each pillar:** `holds`, `at-risk` or `broken`. Check each exit trigger: hit or not.
5. **Decide the verdict:**
   - `intact`: all pillars hold
   - `weakened`: at least one pillar is at risk
   - `broken`: a pillar is broken or an exit trigger was hit. The script refuses `broken` without such evidence.
6. **Save it:**

```bash
... thesis.py check SAP.DE --verdict weakened --summary "..." --pillar-status 1=holds --pillar-status 2=at-risk --conviction medium --source <url>
```

**Present it** in the investor's language:
- a scorecard table: Pfeiler | Erwartung | aktueller Stand (with source) | Status
- the exit triggers and whether any was hit
- the verdict, and how it changed since the last check (from the `log`)
- **"Warum ist das so?"**: what drives the verdict, in plain words at the investor's Explanation Depth

A Thesis check is not a buy or sell recommendation. If the investor wants one, offer the `assess` skill.

## 4. Gaps and reviews

Run `gaps` when the investor asks for an overview, or after `depot` changes. It reports:

| Field | Meaning | What to do |
|---|---|---|
| `missing` | Positions or Watchlist entries without a Thesis | Offer to record one |
| `due_for_review` | Not checked for 90+ days | Offer a check |
| `not_in_depot_or_watchlist` | Probably sold or dropped | Offer to archive |

## 5. Revising and archiving

- **Changing a Thesis on purpose:** use `revise SAP.DE --reason "..." [--statement/--pillar/--exit-trigger ...]`. The previous version stays in the log.
  - Revising is not the same as checking. Revise only when the investor's reason really changes. Don't revise to rescue a broken Thesis without saying so.
- **Position sold:** `archive SAP.DE --reason "verkauft"`. The history stays, and a new Thesis can be recorded later.

## 6. Lite Mode

- Ask the investor for their Thesis in chat, or read it if they paste one.
- Do the check as in section 3, with figures from web search marked as unverified (web search, not a data fetch), with source and date.
- Nothing is saved. Say so.
