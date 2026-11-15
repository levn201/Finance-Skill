# setup scenarios

Run these in Claude Code and Gemini CLI, each with `FINANCIAL_SUPPORT_HOME` pointing to a temporary folder.

## 1. First run in German

> Richte mich bitte ein.

Expected:
- `show` reports that no profile exists
- The skill asks one message in German with four questions, each with its default; it does not ask for the language
- Answering "passt so" creates `profile.json` with `language: de` and the defaults
- The skill offers Finnhub and the SEC setting as optional and warns that a pasted key appears in the chat
- It ends by suggesting `depot`

## 2. Change one weight

> Dividende ist mir wichtiger, gewichte sie mit 25.

Expected:
- The skill proposes where the 10 points come from and asks before saving
- After confirmation, the weights add up to 100
- No other settings change

## 3. Lite Mode

Run this in the Claude app chat:

> Set me up.

Expected:
- The skill says settings can't be saved here
- It asks only for explanation depth and horizon
- It never asks for a key
