# Financial Support

> [!IMPORTANT]
> **Not investment advice.** This project is a personal research assistant. It drafts analysis for your own decisions. It can be wrong, outdated or incomplete, and it never knows your full financial situation. Check every figure and source before acting. You alone are responsible for your investment decisions.

A research assistant for private investors, built as portable [Agent Skills](https://agentskills.io). It knows your Depot and Watchlist and does the following:

- Gives buy, hold or sell **Assessments**, each with a short-term and a medium-term outlook
- Flags upcoming **Catalysts** such as quarterly results, AGMs, dividends and central-bank dates
- Summarises the market and political situation in a **Market Brief**
- Searches for stocks by weighted criteria (a **Screen**)
- Explains *why* things are the way they are, in plain language

It is inspired by [anthropics/financial-services](https://github.com/anthropics/financial-services), cut down to what a private investor needs. The terms used here are defined in [`GLOSSARY.md`](./GLOSSARY.md), and the design decisions are recorded in [`docs/adr/`](./docs/adr).

## Skills

| Skill | What it does | Status |
|---|---|---|
| `setup` | First-run setup: your Investor Profile (screening weights, explanation depth, horizon, risk tolerance) and optional API keys | available |
| `depot` | Remembers your Positions and Watchlist from what you tell it ("I bought 10 SAP at €180"); creates a Depot Snapshot for the apps | available |
| `thesis` | Records why you hold or watch a stock, and checks whether that reason still holds | available |
| `assess` | Buy, hold or sell view on one stock, with short- and medium-term outlook, reasons for and against, and what would change the view | available |
| `catalysts` | Upcoming earnings, AGMs, dividends and central-bank dates for your Depot and Watchlist | available |
| `earnings` | Before results: what's expected. After: what came in and why the price reacted | available |
| `market-brief` | Macro, volatility, politics and geopolitics, and what it means for your Depot | available |
| `depot-review` | Assessment of every Position plus your Watchlist as buy candidates, with a ranked summary | available |
| `screen` | Finds stocks by weighted criteria (fundamentals, dividend, valuation, theme, technicals) | available |
| `valuation` | Fair value range via DCF, what growth the price implies, and peer comparison | available |
| `sector` | Which sectors lead or lag the market and why; one company against its competitors | available |
| `daily` | Unattended weekday run: Catalysts, Market Brief, Depot Review when due, a short Daily Report with a phone notification | available |
| `explain` | Explains terms and connections in plain language ("why does the stock fall despite good results?") | available |
| `market-data` | Internal helper that the other skills use to fetch prices, fundamentals and dates; you don't call it yourself | available |

Outputs answer in the language you write in.

## Install

Full mode needs [`uv`](https://docs.astral.sh/uv/) on your machine (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`). The scripts install their own dependencies on first run. Without `uv` the skills fall back to Lite Mode.

### Claude Code

```bash
claude plugin marketplace add levn201/Finance-Skill
claude plugin install financial-support@financial-support
```

### Claude app (web / desktop, chat and Cowork)

Paid plan required. Go to **Customize → Plugins → +** and choose **Add marketplace**. Enter `levn201/Finance-Skill`, then install **Financial Support**.

In app chat the skills may run in **Lite Mode** (see below).

### Gemini CLI

```bash
gemini extensions install https://github.com/levn201/Finance-Skill
```

### Gemini app and ChatGPT app

These apps take uploaded skills but no plugins, so there is one bundle for both. It always runs in Lite Mode.

1. Build it: `uv run --script scripts/build_app_bundle.py` writes `dist/financial-support.zip`.
2. Upload it:
   - **Gemini:** on gemini.google.com or in the Mac app, open **Settings → Skills → Upload** and choose the ZIP.
   - **ChatGPT:** open **Plugins → Skills** and upload the ZIP.
3. To use your Depot there, ask the `depot` skill in Claude Code or the Gemini CLI for a **Depot Snapshot** and paste or attach it in the chat.

The bundle is generated from `skills/` and never edited by hand. Rebuild and upload it again after an update.

## Full mode and Lite Mode

| | Full mode (Claude Code, Gemini CLI) | Lite Mode (Claude, Gemini and ChatGPT apps) |
|---|---|---|
| Figures | Fetched by bundled scripts (`yfinance`, SEC EDGAR, optional Finnhub) | From web search, marked as unverified |
| Your Depot, Theses, Journal | Stored in `~/.financial-support/` | From a Depot Snapshot you paste or attach; nothing is stored |

Your personal data never lives in this repo or in the plugin folder.

## Daily run

`daily` runs on weekday mornings as a **local scheduled task in the Claude desktop app**. It runs on your Mac, so it can read your Depot in `~/.financial-support/`.

1. In the Claude desktop app, create a new scheduled task (**Code → Scheduled → New task**, the exact menu names may differ):
   - **Trigger:** Weekdays at 07:30, or Custom `30 7 * * 1-5`
   - **Local folder:** this repo
   - **Instructions:** `Read skills/daily/SKILL.md in this folder and follow it exactly.`
2. Click **Run now** once and choose **always allow** for each prompt: `uv run`, web search, web fetch, and writing files to `~/.financial-support/inbox/`, where the run hands its reports to the scripts. Later runs then need no approvals. The run only writes to the inbox and the Journal. It never changes your Depot, Theses or profile.
3. For phone notifications, install the Claude app on your phone and turn on **Settings → Notifications → Scheduled tasks**.
4. In the desktop app, turn on **Keep computer awake**. Runs only start while the app is open and the computer is awake. After sleep, Desktop starts one catch-up run, and the report says it came late.

Each run saves `journal/<date>/daily.md` plus the full Catalysts and Market Brief reports, and the Depot Review when one is due: on Mondays, after results of one of your holdings, or after a move of 5 % or more.

## Optional settings

Everything works without these. Run the `setup` skill to enter them, or set them in your environment:

| Setting | What it adds |
|---|---|
| `FINNHUB_API_KEY` | A free [Finnhub](https://finnhub.io) key gives more reliable earnings dates |
| `SEC_USER_AGENT` | Your name and e-mail (SEC requires a contact) to fetch US filings from SEC EDGAR |

## Development

```bash
uv sync
uv run pytest
uv run --script scripts/build_app_bundle.py   # app bundle in dist/
```

## License

[MIT](./LICENSE)
