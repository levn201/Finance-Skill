# Skills follow the open Agent Skills standard; Claude-specific parts are a thin optional layer

Unlike the upstream `anthropics/financial-services` plugin, which is built as Claude plugins, this project has to work the same way in other AI coding tools (Codex, Gemini CLI, Cursor and others). So every capability lives in a portable `SKILL.md` skill. Claude Code-only features (plugin manifest, marketplace, slash commands, hooks) only wrap those skills and must never contain logic the skills depend on.
