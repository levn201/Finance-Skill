---
name: setup
description: First-run setup and later changes for the financial-support skills. Creates or edits the Investor Profile (explanation depth, default horizon, risk tolerance, screening weights, default language) and the optional settings FINNHUB_API_KEY and SEC_USER_AGENT. Use it when the investor starts out, asks to change a preference or add an API key, or when another skill reports that no Investor Profile exists.
---

# setup

Sets up the investor's standing preferences. Keep it short and friendly. Most investors should be done after one round of questions.

The script used below lives in this skill's directory:

```bash
uv run --script <this skill's directory>/scripts/investor_profile.py <command>
```

Every command prints JSON with `ok`, `error`, `profile` and `settings`. `settings` says whether each key is set and where it comes from, never its value.

## 1. Check the situation

Run `show`.

- **The command can't run** (no shell, no `uv`, or a sandbox without a persistent home directory): you are in **Lite Mode**. Tell the investor that settings can't be saved here and only apply to this conversation. Ask only for explanation depth and horizon, skip keys entirely, then stop.
- **`profile` is `null`**: this is the first run. Continue with section 2.
- **A profile exists**: show the current settings in a compact list and ask what to change. Apply changes with `set` (section 3). Don't repeat the full questionnaire.

## 2. First run: one round of questions

**Language:** don't ask. Use the language the investor writes in and pass it as `init --language <code>` (`de`, `en`, …). It is only the default for unattended runs. Normally every output follows the language of the investor's message.

**If you have a multiple-choice question tool** (e.g. `AskUserQuestion` in Claude Code), ask all four questions in **one call** of that tool, in the investor's language:
- one question per setting, with a short header ("Erklärtiefe", "Horizont", "Risiko", "Gewichtung")
- the default as the first option, marked as recommended, and a one-line description on each option
- for the weights, offer these presets; the tool's free-text option covers custom weights:

| Preset | fundamentals | valuation | dividend | thematic | technical |
|---|---|---|---|---|---|
| Ausgewogen (default) | 30 | 25 | 15 | 15 | 15 |
| Dividende | 25 | 20 | 40 | 5 | 10 |
| Wachstum | 40 | 15 | 5 | 25 | 15 |
| Günstig bewertet | 30 | 40 | 15 | 5 | 10 |

**Otherwise** ask the four questions **in one message**, each with its default so the investor can just say "passt so" or "defaults are fine". Explain each in one plain sentence:

| Setting | Values | Default | Meaning |
|---|---|---|---|
| `explanation_depth` | `beginner`, `advanced` | `beginner` | How much the "Why" part of every answer explains |
| `default_horizon` | `short-term` (weeks to ~3 months), `medium-term` (~6–18 months) | `medium-term` | Which Outlook the overall buy/hold/sell view is based on. Both Outlooks are always shown |
| `risk_tolerance` | `low`, `medium`, `high` | `medium` | How much price swing the investor accepts; used to weigh risks in Assessments |
| screening weights | whole numbers adding up to 100 | fundamentals 30, valuation 25, dividend 15, thematic 15, technical 15 | How much each criterion counts in a Screen |

Briefly explain the five weights:
- **fundamentals**: growth, margins, debt
- **valuation**: cheap or expensive versus peers and the stock's own history
- **dividend**: yield, history, payout ratio
- **thematic**: fits a theme the investor cares about
- **technical**: trend and momentum

Then write the profile:

```bash
... investor_profile.py init --language de
... investor_profile.py set explanation_depth=advanced risk_tolerance=low weights.dividend=25 weights.technical=5
```

## 3. Changing settings

Use `set key=value …` with the keys `language`, `explanation_depth`, `default_horizon`, `risk_tolerance` and `weights.<name>`.

The weights must still add up to 100. If the investor changes one weight, propose where the difference should come from and ask before setting it. Never rebalance silently. If `set` returns an error, explain it in plain words and ask again.

## 4. Optional settings (keys)

Offer both settings and explain them. Both are optional, and everything works without them.

**`FINNHUB_API_KEY`** gives more reliable upcoming earnings dates. It's free at https://finnhub.io/register.

**`SEC_USER_AGENT`** is only needed for filings of US companies. The SEC requires every request to carry a name and e-mail address, which is sent to the SEC with each request. Ask whether the investor wants that before setting it, and never fill it in on their behalf.

Before the investor pastes a value, say that it will appear in this conversation. If they'd rather not, they can do one of these instead:
- set it as an environment variable (`export FINNHUB_API_KEY=...`), which takes precedence over the file
- add `FINNHUB_API_KEY="..."` to `~/.financial-support/.env` themselves

If they give you the value, pass it on stdin so it doesn't end up in the command arguments:

```bash
printf '%s' '<value>' | uv run --script <this skill's directory>/scripts/investor_profile.py set-secret FINNHUB_API_KEY
```

Use `unset-secret <NAME>` to remove one. Never repeat a key back to the investor. "Saved" is enough.

## 5. Finish

Confirm in a few lines what is set, and where (`data_dir`). Then suggest the next step: tell the `depot` skill what you hold and watch, e.g. "Ich habe 10 SAP zu 180 €".

## Profile format

Other skills read this file. The example is in `profile.example.json` in this skill's directory.

`<data dir>/profile.json` contains:
- `version`
- `language`
- `explanation_depth`
- `default_horizon`
- `risk_tolerance`
- `screening_weights` with the keys `fundamentals`, `valuation`, `dividend`, `thematic` and `technical`, adding up to 100
- `updated_at`

The data dir is `~/.financial-support/`, or `$FINANCIAL_SUPPORT_HOME` if set.
