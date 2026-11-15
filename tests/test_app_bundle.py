"""Guards for the generated app bundle (ADR 0006): every workflow is in it, nothing script-only leaks."""

import importlib.util
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("build_app_bundle", ROOT / "scripts" / "build_app_bundle.py")
bab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bab)


def test_bundle_contents(tmp_path):
    out = tmp_path / "bundle.zip"
    files = bab.build(out)
    names = zipfile.ZipFile(out).namelist()
    assert names == sorted(files)
    assert all(n.startswith("financial-support/") for n in names)  # one top-level folder
    assert names.count("financial-support/SKILL.md") == 1
    skills = {p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()}
    assert set(bab.WORKFLOWS) == skills - {"market-data"}, "add new skills to WORKFLOWS (or exclude them on purpose)"
    for name in bab.WORKFLOWS:
        ref = f"references/{name}.md"
        assert f"financial-support/{ref}" in files and f"`{ref}`" in files["financial-support/SKILL.md"]


def test_no_script_only_content_leaks(tmp_path):
    files = bab.build(tmp_path / "bundle.zip")
    for path, text in files.items():
        for bad in bab.FORBIDDEN:
            assert bad not in text, f"{path} contains {bad!r}"
        if path.endswith("references/glossary.md"):
            continue
        if "/references/" in path and path.split("/")[-1][:-3] not in {"explain", "setup"}:
            assert "## " in text and "Lite Mode" in text.split("## ", 2)[1], f"{path}: Lite Mode section must come first"


def test_router_frontmatter(tmp_path):
    router = bab.build(tmp_path / "bundle.zip")["financial-support/SKILL.md"]
    fields, _ = bab.split_frontmatter(router)
    assert fields["name"] == "financial-support" and re.match(r"^[a-z0-9-]{1,64}$", fields["name"])
    assert 0 < len(fields["description"]) <= 1024


def test_build_is_reproducible(tmp_path):
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    bab.build(a)
    bab.build(b)
    assert a.read_bytes() == b.read_bytes()
