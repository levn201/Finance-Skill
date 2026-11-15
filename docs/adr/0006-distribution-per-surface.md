# One skill source, three distribution channels

The same `skills/` sources ship three ways:
1. **As a Claude plugin through this repo's marketplace.** This covers Claude Code and the Claude app (chat and Cowork), which can add a GitHub marketplace directly.
2. **As a Gemini CLI extension** (`gemini-extension.json`) installed from the repo.
3. **As a single generated ZIP bundle for the Gemini app.** It has one routing `SKILL.md` with each workflow as a reference file, because that app only accepts uploaded skills and no plugins.

The bundle is built by a script and never edited by hand, so the channels can't drift apart. Installing from the Claude app needs the repo to be public, or the Claude GitHub App installed on it.
