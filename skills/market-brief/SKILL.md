---
name: market-brief
description: Market Brief (Lagebild). The current market situation covering macro (indices, rates, dollar, oil, gold), volatility (VIX/MOVE), central banks and politics/geopolitics (tariffs, elections, sanctions, conflicts). It always ends with what this means for the investor's Depot and Watchlist, and says what changed since the last brief. Use it when the investor asks "wie ist die Lage?", "was ist am Markt los?", "warum fällt der Markt?", "was bedeutet <politisches Ereignis> für mein Depot?" or wants a daily or weekly market overview.
---

# market-brief

Explains what is moving markets and why, and connects it to the investor's own Positions and Watchlist. Politics is a section here, not a separate product. It matters through its effect on markets.

```bash
uv run --script <this skill's directory>/scripts/brief.py data
uv run --script <this skill's directory>/scripts/brief.py save --input <inbox>/market-brief.json
```

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3` (the scripts need Python 3.11+ and their own dependencies):

```bash
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
```

## 1. Facts

1. Run market-data `status`. In Lite Mode, see section 5.
2. Run `brief.py data`. It returns:

| Field | Contents |
|---|---|
| `indicators` | Indices: S&P 500, Nasdaq 100, DAX, Euro Stoxx 50 |
| | Volatility: VIX, MOVE |
| | Rates: US 10y and 3m yields |
| | Currencies and commodities: EUR/USD, US dollar index, Brent, gold |
| `vix_regime` | Rule-of-thumb volatility regime |
| `yield_curve` | 10y−3m spread and whether the curve is inverted |
| `depot_exposure` | Depot weights by sector, country and currency |
| `holdings` | Sector and country of every Position and Watchlist entry |

   Each indicator has its last value, the change over 1 day, 1 week and 1 month, and its 1-year percentile.
3. Use web search for what the data doesn't cover, covering roughly the last 1–2 weeks and preferring primary or established sources:
   - **Central banks:** latest ECB and Fed decisions and communication, and market expectations for the next meeting
   - **Euro-area rates:** the Bund 10y yield, and the VSTOXX if volatility matters
   - **Macro data:** inflation, labour market, PMIs, growth surprises
   - **Politics and geopolitics:** trade policy and tariffs, elections, budget disputes, sanctions, conflicts
   - **Sectors:** news for the sectors in `depot_exposure` and the Watchlist

   Search specifically for what affects the investor's holdings. For example, with ASML on the Watchlist, look at export controls on chip machines.

## 2. Judge

- **`regime`:** start from `vix_regime`, and adjust if other signals clearly disagree (MOVE, sharp index drops, credit stress). Say why.
- **Themes:** pick the **3–6 themes** that actually drive markets now. Each theme gets:
  - a `category`: macro, central_banks, politics, geopolitics, trade, sector or other
  - a `direction` for markets: positive, neutral, negative or uncertain
  - `affects`: the investor's symbols it touches
  - `sources` with dates
- **Rumours:** separate facts from speculation. A rumour is marked as one, and a forecast is not a fact.
- **`depot_impact`:** 2–4 sentences, specific to this Depot. Cover concentration (e.g. 100 % tech is sensitive to rate rises), currency (dollar strength or weakness on US holdings) and the themes that hit specific Positions.

## 3. Save, then present

Write the JSON with your file-writing tool to `<inbox>/market-brief.json` and pass `--input <that file>`. `<inbox>` is the `inbox` path from market-data `status`. The script deletes the file after a successful save. Don't put JSON in the shell command itself: Claude Code blocks commands that contain `{"`.

The brief looks like this:

```json
{"regime": "normal", "indicators": <data.indicators>,
 "themes": [{"title": "US-Exportkontrollen für Chipmaschinen", "category": "trade", "direction": "negative",
             "affects": ["ASML.AS"], "sources": [{"name": "...", "url": "...", "as_of": "2026-11-12"}]}],
 "depot_impact": "...", "report_markdown": "<the full answer, without 'Seit dem letzten Lagebild'>"}
```

It returns `diff`: regime change, VIX then versus now, new and dropped themes, and changed directions.

Present in the investor's language:

1. **Lage in drei Sätzen:** the regime and the main driver.
2. **Märkte:** a compact table of the indicators with value, 1W and 1M change. Comment only on what stands out, for example the gold price at the low end of its 1-year range, or the dollar index at the high end.
3. **Notenbanken & Zinsen:** decisions, expectations, the yield curve and what that means.
4. **Politik & Geopolitik:** one block per theme. Say what happened and why it matters for markets, with sources.
5. **Was heißt das für dein Depot?:** the `depot_impact`, then per affected Position or Watchlist entry one line on the effect.
   - No buy or sell recommendations here. Offer `assess` or `depot-review` for those.
   - Point to critical dates if `catalysts` knows any.
6. **Seit dem letzten Lagebild:** from `diff`. Skip this on the first brief.
7. **Warum ist das so?:** the 2–3 mechanisms behind today's picture, in plain words at the investor's Explanation Depth. For example:
   - why rising yields weigh on growth stocks
   - why a strong dollar lowers the euro value of US shares
   - why tariffs hit exporters
8. **Quellen** with dates.

## 4. Single questions

If the investor asks about one event ("was bedeuten die neuen Zölle für mich?"):
- Research it, explain the mechanism, and connect it to the affected holdings.
- Don't save, unless it turns into a full brief.

## 5. Lite Mode

- Get index levels, VIX, yields and commodities by web search, marked as unverified (web search, not a data fetch), with source and date.
- Take the Depot from a Depot Snapshot or the chat.
- Nothing is saved, so there is no "Seit dem letzten Lagebild". Say so.

## Support hint

End your first answer in a conversation with this line, in the investor's language, unless `support` already ran in it:

> Nicht sicher, welcher Skill passt? Frag „Was kannst du?“ oder ruf `/financial-support:support` auf.

In Lite Mode, leave out the command.
