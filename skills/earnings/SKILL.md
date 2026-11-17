---
name: earnings
description: Quarterly results for one stock. Before the results (preview): the date, what is expected (EPS and revenue consensus, estimate revisions), what to watch, the company's beat history and how strongly the stock usually reacts. After the results (review): actual versus expected, guidance, and why the price reacted the way it did. Use it when the investor asks "was wird von den SAP-Zahlen erwartet?", "wie waren die Zahlen von Apple?", "warum fällt X nach den Zahlen?", or before or after an earnings date from catalysts.
---

# earnings

Gets the investor ready for results and explains them afterwards.

```bash
uv run --script <this skill's directory>/scripts/earnings.py <symbol or ISIN>
```

The script returns:

| Field | Contents |
|---|---|
| `mode` | `review` if results came out in the last 10 days, otherwise `preview`. Follow the investor if they ask for the other one. |
| `next` | The next date, always an estimate from Yahoo |
| `consensus` | Quarter and year EPS and revenue (avg, low, high, number of analysts, growth versus a year ago), plus `eps_revision`, i.e. how the quarter's EPS estimate moved over 30 and 90 days |
| `track_record` | The last 8 quarters (estimate, reported, surprise, price reaction from the close before to the close after), the beat rate, the average and largest move, and `beat_but_fell` |
| `last_reported`, `quote` | The latest results and the current quote |

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3`:

```bash
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
uv run --script <this skill's directory>/../setup/scripts/investor_profile.py show
uv run --script <this skill's directory>/../thesis/scripts/thesis.py show <SYMBOL>
uv run --script <this skill's directory>/../depot/scripts/depot.py show
```

## 0. Pick the right symbol

Run `depot.py show` first. If the Instrument is a Position or on the Watchlist, use **exactly that symbol** for everything: this script, the Thesis and market-data. For example, use `SAP.DE`, not the US ADR `SAP`.

Otherwise use the company's home listing (market-data `resolve`). A foreign listing has estimates in another currency, from fewer analysts, and its estimate trend mixes in exchange-rate moves.

## 1. Preview (before the results)

1. **Date:** run `earnings.py`. Confirm the date on the company's IR calendar by web search. If you can't, say that it's an estimate.
2. **Expectations:** EPS and revenue consensus with range and number of analysts. Add the company's own guidance from its last report or call (web search, IR first).
   - Pass on the `eps_revision`. Falling estimates lower the bar, rising ones raise it.
3. **What to watch:** the 3–5 points the market will judge, from recent reports and commentary. For example: the cloud growth rate and current cloud backlog at SAP, iPhone demand and China at Apple, orders at ASML.
   - If there is a Thesis (`thesis.py show`), map them to its pillars. "These results test pillar 1".
4. **How the stock usually reacts:**
   - beat rate and average surprise
   - average and largest move around results, e.g. "typically ±4.6 %, at most 13 %"
   - if `beat_but_fell` isn't empty, point it out and explain it. It is common: the market reacts to guidance and to expectations beyond the consensus.
5. **Scenarios:** a short table (better than expected / in line / worse) with what each would likely mean. Phrase it as likely, not certain.

## 2. Review (after the results)

1. **Actual versus expected:** EPS and revenue versus consensus, from `last_reported` and web search, ideally the company's release.
2. **Beyond the headline numbers:** guidance changes and segment figures, plus key quotes from the call if available.
3. **The price reaction:** from `quote`, or `history` for the days after.
4. **Why the stock moved:** explain it, separating confirmed points (company figures, guidance) from interpretation (commentary).
   - If the stock fell despite a beat, name the usual causes and which ones apply here: weak guidance, a key metric missed, high expectations already priced in, or market-wide moves on the same day.
5. **Thesis:** if one exists, say which pillars the results strengthen or weaken. Offer to log that as a data point with `thesis.py log`.

## 3. Output

Present in the investor's language:

1. **Kurz gesagt:** 2–3 sentences.
2. **Erwartungen** or **Ergebnis vs. Erwartung:** a table.
3. **Worauf es ankommt** (preview) or **Was den Kurs bewegt hat** (review).
4. **Wie die Aktie sonst reagiert:** from the track record.
5. **Warum ist das so?:** at the investor's Explanation Depth. For example, why the price reacts to the difference from expectations rather than to "good" or "bad" numbers.
6. **Quellen** with dates.

Every figure needs a source and date, and estimates are marked as estimates. No buy or sell view: offer `assess` if the investor wants one. Mention that the `catalysts` skill shows all upcoming dates.

## 4. Lite Mode

- Get the consensus, results and reaction by web search, marked as unverified (web search, not a data fetch), with source and date.
- Skip the multi-quarter track record unless a reliable source lists it, and say so.

## Support hint

End your first answer in a conversation with this line, in the investor's language, unless `support` already ran in it:

> Nicht sicher, welcher Skill passt? Frag „Was kannst du?“ oder ruf `/financial-support:support` auf.

In Lite Mode, leave out the command.
