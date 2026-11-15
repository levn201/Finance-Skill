# /// script
# requires-python = ">=3.11"
# ///
"""Build the app bundle: one Lite-Mode skill for the Gemini and ChatGPT apps (ADR 0005, ADR 0006).

    uv run --script scripts/build_app_bundle.py            # writes dist/financial-support.zip

The bundle is generated from skills/*/SKILL.md and GLOSSARY.md and never edited by hand. It holds one routing
SKILL.md plus one reference file per workflow, with everything that needs scripts or stored data removed.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
BUNDLE = "financial-support"
OUT = ROOT / "dist" / f"{BUNDLE}.zip"

# Workflows in the bundle, in routing order. market-data is not a workflow: its Lite Mode rules go into SKILL.md.
WORKFLOWS = ["assess", "depot-review", "depot", "thesis", "catalysts", "earnings", "valuation",
             "sector", "market-brief", "screen", "explain", "setup"]
DROP_ALWAYS = {"Scripts of other skills", "Settings", "Profile format"}
DROP = {  # sections that only make sense with scripts and stored data; the build fails if a heading disappears
    "assess": ["5. Save to the Journal"],
    "depot-review": ["3. Save the review"],
    "setup": ["4. Optional settings (keys)"],
    "depot": ["4. Base currency", "5. Depot Snapshot"],
}
FORBIDDEN = ("uv run", "--script", "Scripts of other skills")  # must never reach the bundle
DESCRIPTION = (
    "Research assistant for a private investor in German, EU and US stocks and ETFs (app edition). "
    "Gives buy, hold or sell Assessments with short- and medium-term Outlook, checks the whole Depot, "
    "lists upcoming earnings and other critical dates, previews and explains quarterly results, estimates "
    "fair value, compares sectors and competitors, briefs on markets, macro and politics, screens for stocks "
    "and tracks the investor's Thesis, always explaining why. Figures come from web search with sources. "
    "Use it for any question about a stock, an ETF, the investor's Depot or the markets, e.g. \"Soll ich SAP "
    "kaufen?\", \"Wie steht mein Depot?\", \"Wann kommen die Apple-Zahlen?\", \"Was ist an den Märkten los?\"."
)
BANNER = (
    "> **App edition, Lite Mode.** No scripts run here and nothing is stored. Wherever the steps below name "
    "a script, a command or a saved file, get the same facts by web search instead and follow the Lite Mode "
    "rules in `SKILL.md`. The Lite Mode section directly below takes precedence over the rest.\n"
)


class BuildError(RuntimeError):
    pass


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise BuildError("SKILL.md without frontmatter")
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields, text[m.end():]


def sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    """(text before the first '## ' heading, [(heading, section text incl. heading), ...]), ignoring code fences."""
    head, out, current, title, fence = [], [], None, None, False
    for line in body.splitlines(keepends=True):
        if line.startswith("```"):
            fence = not fence
        if not fence and line.startswith("## "):
            if current is not None:
                out.append((title, "".join(current)))
            title, current = line[3:].strip(), [line]
        elif current is None:
            head.append(line)
        else:
            current.append(line)
    if current is not None:
        out.append((title, "".join(current)))
    return "".join(head), out


def strip_script_blocks(text: str) -> str:
    """Remove fenced code blocks that run scripts, and lines that only introduce a script call."""
    text = re.sub(r"```[a-z]*\n(?:(?!```).)*?(?:uv run|--script)(?:(?!```).)*?```\n?", "", text, flags=re.DOTALL)
    text = re.sub(r"^.*\bon stdin with a quoted heredoc.*\n", "", text, flags=re.MULTILINE)
    return re.sub(r"\n{3,}", "\n\n", text)


def lite_reference(name: str, text: str) -> str:
    _, body = split_frontmatter(text)
    head, secs = sections(body)
    titles = [t for t, _ in secs]
    for wanted in DROP.get(name, []):
        if wanted not in titles:
            raise BuildError(f"{name}: section '## {wanted}' not found; update DROP in build_app_bundle.py")
    drop = DROP_ALWAYS | set(DROP.get(name, []))
    lite = [s for t, s in secs if "Lite Mode" in t]
    rest = [s for t, s in secs if t not in drop and "Lite Mode" not in t]
    title, _, intro = head.strip().partition("\n")
    out = "\n".join([title, "", BANNER, *lite, intro.strip() + "\n", *rest])
    out = strip_script_blocks(out)
    for bad in FORBIDDEN:
        if bad in out:
            raise BuildError(f"{name}: '{bad}' left in the reference; move it into a dropped section or a code block")
    return out.rstrip() + "\n"


def section_text(text: str, title: str) -> str:
    _, secs = sections(split_frontmatter(text)[1])
    for t, s in secs:
        if t == title:
            return s.split("\n", 1)[1].strip()
    raise BuildError(f"section '## {title}' not found")


def router(descriptions: dict[str, str], data_rules: str) -> str:
    rows = "\n".join(f"| `references/{n}.md` | {descriptions[n]} |" for n in WORKFLOWS)
    return f"""---
name: {BUNDLE}
description: {DESCRIPTION}
---

# financial-support (app edition)

A research assistant for a private investor. This is the Lite Mode edition for chat apps: no scripts, no stored data. The full edition with live data, a saved Depot and a Journal runs in Claude Code and the Gemini CLI.

## How to work

1. Pick the workflow from the table below that fits the investor's message, and **read its reference file before answering**. If several fit, start with the first and offer the others at the end.
2. Use the terms in `references/glossary.md` (Depot, Position, Watchlist, Assessment, Thesis, …).
3. Follow the rules below in every answer.

| Read | When |
|---|---|
{rows}

## Lite Mode rules

{data_rules}

## The investor's Depot

- If the conversation or an attached file contains a block starting with `FINANCIAL-SUPPORT DEPOT SNAPSHOT v1`, read Positions and Watchlist from it. It is a read-only copy made in the full edition.
- Otherwise ask what the investor holds and watches. Accept changes for this conversation only and say they aren't saved.
- If no Investor Profile is known, assume medium-term horizon, medium risk tolerance and beginner explanation depth, and say so once.

## Rules for every answer

- **Language:** answer in the language the investor writes in.
- **Figures:** every figure has a source and a date and is marked **unverified (web search, not a data fetch)**. Unknown is "unclear". Never use a number from memory.
- **Why:** end with a "Warum ist das so?" section in plain words, at the investor's explanation depth.
- **No sizing:** give views, never a position size, an amount or a share count.
- **Disclaimer:** close with "Keine Anlageberatung: eine Einschätzung zur eigenen Entscheidung, kann falsch sein." (in the investor's language).
"""


def build(out: Path = OUT) -> dict[str, str]:
    files: dict[str, str] = {}
    descriptions = {}
    for name in WORKFLOWS:
        text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
        fields, _ = split_frontmatter(text)
        desc = fields["description"]
        when = desc[desc.find("Use it "):] if "Use it " in desc else desc  # the trigger part routes best
        descriptions[name] = when.replace("Use it when the investor", "The investor").replace("Use it whenever", "Whenever").replace("|", "/")
        files[f"{BUNDLE}/references/{name}.md"] = lite_reference(name, text)
    data_rules = section_text((SKILLS / "market-data" / "SKILL.md").read_text(encoding="utf-8"), "5. Lite Mode")
    files[f"{BUNDLE}/SKILL.md"] = router(descriptions, data_rules)
    files[f"{BUNDLE}/references/glossary.md"] = (ROOT / "GLOSSARY.md").read_text(encoding="utf-8")
    if len(DESCRIPTION) > 1024:
        raise BuildError("description longer than 1024 characters")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(files):
            info = zipfile.ZipInfo(path, date_time=(2026, 1, 1, 0, 0, 0))  # fixed time: identical builds
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, files[path])
    return files


def main() -> int:
    try:
        files = build()
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {OUT.relative_to(ROOT)} ({len(files)} files, {OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
