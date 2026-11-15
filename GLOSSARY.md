# Financial Support

A personal research assistant for a private investor: it watches the investor's holdings and candidates, surfaces upcoming risks and opportunities, forms reasoned buy/sell views, and explains the reasoning in plain language. Canonical terms are English; the German term is what appears in German output.

## Holdings

**Instrument** (DE: _Wert_):
A tradeable security in scope: a US, German or EU-listed stock, or an ETF.
_Avoid_: Titel, Asset, Ticker (a ticker only identifies an Instrument)

**Depot** (DE: _Depot_):
The set of Positions the investor actually holds, as the investor has told the assistant.
_Avoid_: Portfolio, Account

**Position** (DE: _Position_):
A single Instrument held in the Depot, with quantity and entry price.
_Avoid_: Holding, Investment

**Depot Snapshot** (DE: _Depot-Snapshot_):
A short, read-only text copy of the Depot and Watchlist that the investor carries into an app where the Depot itself can't be reached.
_Avoid_: Export, Backup

**Watchlist** (DE: _Watchlist_):
Instruments the investor observes as potential buys but does not hold.
_Avoid_: Favoriten, Beobachtungsliste

## Analysis

**Catalyst** (DE: _Termin_):
A dated future event likely to move an Instrument's price, such as quarterly results, an AGM, an ex-dividend date or a central-bank meeting.
_Avoid_: Event, Datum, Trigger

**Market Brief** (DE: _Lagebild_):
A snapshot of the current market situation covering macro/volatility and politics/geopolitics, always ending with what it means for the Depot and Watchlist.
_Avoid_: Morning Note, Marktbericht, Politik-Analyse (politics is a section, not a separate product)

**Screen** (DE: _Screening_):
A search across Instruments that scores each against weighted criteria and returns ranked candidates.
_Avoid_: Filter, Scan

**Assessment** (DE: _Einschätzung_):
A reasoned buy, hold or sell view on one Instrument, with a separate Outlook per Horizon, the reasons for and against, and what would invalidate the view. Never includes a position size. For an Instrument the investor doesn't hold, hold means "wait" and sell means "don't buy".
_Avoid_: Empfehlung, Rating, Signal

**Horizon** (DE: _Zeithorizont_):
The time frame an Outlook refers to: short-term (weeks up to about 3 months) or medium-term (about 6–18 months, the default for the overall view).
_Avoid_: Laufzeit, Zeitraum

**Outlook** (DE: _Ausblick_):
The expected direction and main drivers for one Instrument within one Horizon, e.g. "high potential next year, but short-term swings from rising competition".
_Avoid_: Prognose, Kursziel

**Depot Review** (DE: _Depot-Check_):
An Assessment of every Position in the Depot and every Instrument on the Watchlist at once, summarised into what to buy, hold or sell. Watchlist Instruments appear as buy candidates.
_Avoid_: Portfolio-Analyse, Rebalancing

**Thesis** (DE: _These_):
The investor's recorded reason for holding or watching an Instrument, which Assessments test for whether it still holds.
_Avoid_: Begründung, Story

## Explanation

**Why Section** (DE: _Warum ist das so?_):
The plain-language part of every output that explains the causes behind a finding.
_Avoid_: Fazit, Summary

**Explanation Depth** (DE: _Erklärtiefe_):
The investor's chosen level of explanatory detail, beginner or advanced.
_Avoid_: Modus, Level

## Investor context

**Investor Profile** (DE: _Anlegerprofil_):
The investor's standing preferences: screening weights, Explanation Depth, default Horizon, risk tolerance, and a default language used only when there is no message to follow (output otherwise answers in the language the investor writes in).
_Avoid_: Settings, Config

**Lite Mode** (DE: _Lite-Modus_):
How a skill runs where it can't reach live data or stored investor context: figures come from web search and are marked unverified, and nothing is stored.
_Avoid_: Offline-Modus, App-Modus

**Journal** (DE: _Journal_):
The dated record of past outputs, used to show what changed since the previous run.
_Avoid_: History, Log, Archiv
