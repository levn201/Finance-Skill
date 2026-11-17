---
name: depot
description: Keeps the investor's Depot (Positions with quantity and entry price) and Watchlist from what they say in chat, e.g. "Ich habe 10 SAP zu 180 € gekauft", "verkaufe die Hälfte meiner Apple", "setz ASML auf die Watchlist". Shows the Depot with current value, profit/loss and weights, and creates a Depot Snapshot to use in the Claude or Gemini app. Use it whenever the investor mentions buying, selling, holding or watching an Instrument, or asks what is in their Depot.
---

# depot

Remembers what the investor holds and watches. The investor talks naturally, and you turn that into exact changes.

```bash
uv run --script <this skill's directory>/scripts/depot.py <command>
```

Every command prints JSON with `ok`, `error`, `notes`, `warnings` and `depot`. The data lives in `<data dir>/depot.json`.

## Scripts of other skills

The other financial-support skills sit next to this skill's directory. Run their scripts exactly like this, always with `uv run --script`, never with plain `python3` (the scripts need Python 3.11+ and their own dependencies):

```bash
uv run --script <this skill's directory>/../market-data/scripts/fetch.py <command>
```

## 1. Mode

If the script can't run, you are in **Lite Mode** (section 6).

## 2. Understanding the investor

Turn each statement into a command. For every Instrument that is new to the Depot or Watchlist, run market-data `resolve` (and `quote` if needed) first. That gives you the exact symbol, name and currency.

Rules for the symbol:
- **German/EU stocks:** use the home listing, e.g. `SAP.DE` rather than the US ADR `SAP`.
- **US stocks:** use the US ticker (`AAPL`). Investors at German brokers like Scalable often buy them in EUR, so the entry price is in EUR. Pass `--entry-currency EUR` whenever the investor's price is in euros ("zu 180 €"). If the currency of the price is unclear, ask.
- **Ambiguous match** (several companies or share classes): ask which one, listing at most three options.

| The investor says | Command |
|---|---|
| "Ich habe 10 SAP zu 180 €" (not yet in the Depot) | `add SAP.DE --quantity 10 --entry-price 180 --name "SAP SE"` |
| "Ich habe Apple" (nothing else known) | `add AAPL --name "Apple Inc."`, with quantity and entry price left out |
| "Hab 5 SAP für 210 nachgekauft" | `buy SAP.DE --quantity 5 --price 210` (the entry price becomes the average) |
| "Ich hab doch 12 SAP, nicht 10" | `update SAP.DE --quantity 12` (a correction, not a purchase) |
| "4 SAP verkauft" | `sell SAP.DE --quantity 4` |
| "SAP komplett verkauft" | `sell SAP.DE` |
| "Setz ASML auf die Watchlist, warte auf einen Rücksetzer" | `watch ASML.AS --name "ASML Holding" --note "wait for a dip"` |
| "ASML interessiert mich nicht mehr" | `unwatch ASML.AS` |

How to handle edge cases:
- **Purchase or correction?** If it's unclear whether shares were added or a number is being corrected, ask.
- **Several Instruments in one message:** run one command each, then confirm them all together.
- **After a change:** confirm it in one short line, e.g. "Gespeichert: 10 SAP zu 180 €". Pass on any `notes`, for example that the Instrument was moved off the Watchlist.
- **New Position or Watchlist entry:** offer once to record why the investor bought or watches it. That reason is the Thesis, recorded by the `thesis` skill.

## 3. Showing the Depot

Run `show --prices` and present a table with these columns:
- Name (symbol)
- Stück
- Einstand
- Kurs
- Wert
- G/V in € and %
- Gewicht

Then add the totals in the base currency.

- Missing values are shown as "–" and never estimated.
- Pass on every warning that matters. The script warns about:
  - concentration, i.e. a single stock at 25 % or more (ETFs excluded)
  - profit/loss totals that cover only some Positions
  - entry prices in another currency
  - missing prices or exchange rates
- Cite the price source and date from `sources`, and the rates from `fx_rates`.

End with a short **"Warum ist das so?"** that explains the notable points at the investor's Explanation Depth. For example: why a 30 % single-stock weight is a cluster risk, or why exchange rates change the profit/loss on US shares bought in euros.

Pure change confirmations don't need this.

The Watchlist is shown below the table as a list, with notes.

## 4. Base currency

All values are in the base currency (default EUR). Change it with `base-currency <CODE>` only when the investor asks.

## 5. Depot Snapshot

When the investor wants to use an app (Claude, Gemini or ChatGPT), run `snapshot` and give them the `snapshot` text in a code block. It also carries the active Theses and the Investor Profile's language, explanation depth, horizon and risk tolerance. Tell them where it goes:
- **Claude app:** add it to a Project's knowledge, or paste it into the chat.
- **Gemini or ChatGPT app:** attach it as a file or paste it.

The snapshot is a read-only copy. Remind the investor to create a new one after changes.

## 6. Lite Mode

- **Reading the Depot:** if the conversation contains a Depot Snapshot (a block starting with `FINANCIAL-SUPPORT DEPOT SNAPSHOT v1`), read Positions and Watchlist from it, and use its `PROFILE` and `THESES` parts if present. Otherwise ask the investor what they hold.
- **Changes:** accept them for this conversation only. Say clearly that nothing is saved and that they should make the change in Claude Code or the Gemini CLI to keep it.
- **Values:** get prices from web search, marked as unverified (web search, not a data fetch), with source and date. Do the same calculations as in section 3 and show the arithmetic so it can be checked.

## Support hint

End your first answer in a conversation with this line, in the investor's language, unless `support` already ran in it:

> Nicht sicher, welcher Skill passt? Frag „Was kannst du?“ oder ruf `/financial-support:support` auf.

In Lite Mode, leave out the command.
