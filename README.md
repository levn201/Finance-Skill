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
| `setup` | First-run setup: your Investor Profile (screening weights, explanation depth, horizon, risk tolerance) and optional API keys | planned ([#4](https://github.com/levn201/Financial-Support-Skill/issues/4)) |
| `depot` | Remembers your Positions and Watchlist from what you tell it ("I bought 10 SAP at €180"); creates a Depot Snapshot for the apps | planned ([#5](https://github.com/levn201/Financial-Support-Skill/issues/5)) |
| `thesis` | Records why you hold or watch a stock, and checks whether that reason still holds | planned ([#6](https://github.com/levn201/Financial-Support-Skill/issues/6)) |
| `assess` | Buy, hold or sell view on one stock, with short- and medium-term outlook, reasons for and against, and what would change the view | planned ([#7](https://github.com/levn201/Financial-Support-Skill/issues/7)) |
| `catalysts` | Upcoming earnings, AGMs, dividends and central-bank dates for your Depot and Watchlist | planned ([#8](https://github.com/levn201/Financial-Support-Skill/issues/8)) |
| `earnings` | Before results: what's expected. After: what came in and why the price reacted | planned ([#9](https://github.com/levn201/Financial-Support-Skill/issues/9)) |
| `market-brief` | Macro, volatility, politics and geopolitics, and what it means for your Depot | planned ([#10](https://github.com/levn201/Financial-Support-Skill/issues/10)) |
| `depot-review` | Assessment of every Position plus your Watchlist as buy candidates, with a ranked summary | planned ([#11](https://github.com/levn201/Financial-Support-Skill/issues/11)) |
| `screen` | Finds stocks by weighted criteria (fundamentals, dividend, valuation, theme, technicals) | planned ([#12](https://github.com/levn201/Financial-Support-Skill/issues/12)) |
| `valuation` | Fair value via DCF and peer comparison | planned ([#13](https://github.com/levn201/Financial-Support-Skill/issues/13)) |
| `sector` | Sector overview and competitors | planned ([#14](https://github.com/levn201/Financial-Support-Skill/issues/14)) |
| `explain` | Explains terms and connections in plain language ("why does the stock fall despite good results?") | planned ([#15](https://github.com/levn201/Financial-Support-Skill/issues/15)) |
| `market-data` | Internal helper that the other skills use to fetch prices, fundamentals and dates; you don't call it yourself | planned ([#3](https://github.com/levn201/Financial-Support-Skill/issues/3)) |

Outputs answer in the language you write in.

## Install

### Claude Code

```bash
claude plugin marketplace add levn201/Financial-Support-Skill
claude plugin install financial-support@financial-support
```

### Claude app (web / desktop, chat and Cowork)

Paid plan required. Go to **Customize → Plugins → +** and choose **Add marketplace**. Enter `levn201/Financial-Support-Skill`, then install **Financial Support**.

In app chat the skills may run in **Lite Mode** (see below).

### Gemini CLI

```bash
gemini extensions install https://github.com/levn201/Financial-Support-Skill
```

### Gemini app

Upload `dist/financial-support.zip` as a skill (gemini.google.com or the Mac app). The ZIP is built by a script, which is not available yet ([#16](https://github.com/levn201/Financial-Support-Skill/issues/16)). The Gemini app always runs in Lite Mode.

## Full mode and Lite Mode

| | Full mode (Claude Code, Gemini CLI) | Lite Mode (apps) |
|---|---|---|
| Figures | Fetched by bundled scripts (`yfinance`, SEC EDGAR, optional Finnhub) | From web search, marked as unverified |
| Your Depot, Theses, Journal | Stored in `~/.financial-support/` | From a Depot Snapshot you paste or attach; nothing is stored |

Your personal data never lives in this repo or in the plugin folder.

## Optional API key

Everything works without keys. A free [Finnhub](https://finnhub.io) key improves catalyst dates and news. Run the `setup` skill to enter it, or set `FINNHUB_API_KEY` in your environment.

## Development

```bash
uv sync
uv run pytest
```

## License

[MIT](./LICENSE)
