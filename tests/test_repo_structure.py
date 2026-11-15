"""Guards for the repo layout: manifests agree, skills are well-formed, README lists every skill."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())


def frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, f"{skill_md} has no YAML frontmatter"
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def test_manifests_agree_on_name_and_version():
    plugin = load_json(".claude-plugin/plugin.json")
    marketplace = load_json(".claude-plugin/marketplace.json")
    gemini = load_json("gemini-extension.json")

    assert plugin["name"] == gemini["name"] == "financial-support"
    assert plugin["version"] == gemini["version"]
    assert [p["name"] for p in marketplace["plugins"]] == [plugin["name"]]
    assert marketplace["plugins"][0]["source"] == "./"


def test_every_skill_is_well_formed():
    for skill in skill_dirs():
        skill_md = skill / "SKILL.md"
        assert skill_md.is_file(), f"{skill.name} has no SKILL.md"
        fields = frontmatter(skill_md)
        assert fields.get("name") == skill.name, f"{skill.name}: frontmatter name must match folder"
        assert NAME_RE.match(skill.name), f"{skill.name}: lowercase letters, digits and hyphens only"
        assert fields.get("description"), f"{skill.name}: description is required"


def test_cross_skill_scripts_have_exact_commands():
    """A skill that mentions another skill's script must show the exact `../<skill>/scripts/<file>` path.

    Without it, agents guess the command (e.g. plain python3 on a too-old system Python) and fail.
    """
    owners = {p.name: skill.name for skill in skill_dirs() for p in (skill / "scripts").glob("*.py")}
    for skill in skill_dirs():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        for script, owner in owners.items():
            if owner == skill.name or not re.search(rf"\b{re.escape(script)}\b", text):
                continue
            assert f"../{owner}/scripts/{script}" in text, (
                f"{skill.name}/SKILL.md mentions {script} but not the command path ../{owner}/scripts/{script}"
            )


def test_readme_lists_every_skill():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"^\| `([a-z0-9-]+)` \|", readme, re.MULTILINE))
    missing = {s.name for s in skill_dirs()} - listed
    assert not missing, f"README skill table is missing: {sorted(missing)}"
