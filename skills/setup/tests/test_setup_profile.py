import json
import stat
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(SKILL.parent / "market-data" / "scripts"))

import core as market_core  # noqa: E402
import investor_profile as prof  # noqa: E402


@pytest.fixture
def env(tmp_path):
    return {"FINANCIAL_SUPPORT_HOME": str(tmp_path / "fs")}


def test_init_creates_default_profile_once(env):
    first = prof.run(["init", "--language", "DE"], environ=env)
    assert first["ok"] and first["created"]
    assert first["profile"]["language"] == "de"
    assert first["profile"]["screening_weights"] == prof.DEFAULT_WEIGHTS
    again = prof.run(["init", "--language", "en"], environ=env)
    assert again["created"] is False and again["profile"]["language"] == "de"


def test_set_changes_single_settings(env):
    prof.run(["init", "--language", "de"], environ=env)
    r = prof.run(["set", "explanation_depth=advanced", "risk_tolerance=HIGH"], environ=env)
    assert r["ok"]
    saved = json.loads((Path(env["FINANCIAL_SUPPORT_HOME"]) / "profile.json").read_text())
    assert saved["explanation_depth"] == "advanced" and saved["risk_tolerance"] == "high"
    assert saved["default_horizon"] == "medium-term"


def test_weights_must_add_up_to_100(env):
    prof.run(["init", "--language", "de"], environ=env)
    bad = prof.run(["set", "weights.fundamentals=40"], environ=env)
    assert not bad["ok"] and "add up to 100" in bad["error"]
    good = prof.run(["set", "weights.fundamentals=40", "weights.technical=5"], environ=env)
    assert good["ok"] and sum(good["profile"]["screening_weights"].values()) == 100


@pytest.mark.parametrize("assignment", ["risk_tolerance=extreme", "colour=blue", "weights.luck=5", "language=123", "weights.dividend=x"])
def test_invalid_settings_are_rejected_and_not_saved(env, assignment):
    prof.run(["init", "--language", "de"], environ=env)
    before = (Path(env["FINANCIAL_SUPPORT_HOME"]) / "profile.json").read_text()
    assert not prof.run(["set", assignment], environ=env)["ok"]
    assert (Path(env["FINANCIAL_SUPPORT_HOME"]) / "profile.json").read_text() == before


def test_set_without_profile_fails(env):
    r = prof.run(["set", "risk_tolerance=low"], environ=env)
    assert not r["ok"] and "init" in r["error"]


def test_secrets_are_stored_private_and_never_printed(env):
    r = prof.run(["set-secret", "FINNHUB_API_KEY"], stdin="  sk-secret-123\n", environ=env)
    assert r["ok"] and "sk-secret-123" not in json.dumps(r)
    assert r["settings"]["FINNHUB_API_KEY"] == {"set": True, "source": "file", "purpose": prof.SECRETS["FINNHUB_API_KEY"]}
    env_file = Path(env["FINANCIAL_SUPPORT_HOME"]) / ".env"
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600


def test_secret_with_spaces_is_readable_by_market_data(env):
    prof.run(["set-secret", "SEC_USER_AGENT"], stdin="Jane Doe jane@example.com", environ=env)
    prof.run(["set-secret", "FINNHUB_API_KEY"], stdin="abc", environ=env)
    assert market_core.get_setting("SEC_USER_AGENT", env) == "Jane Doe jane@example.com"
    assert market_core.get_setting("FINNHUB_API_KEY", env) == "abc"


def test_unset_secret_and_environment_source(env):
    prof.run(["set-secret", "FINNHUB_API_KEY"], stdin="abc", environ=env)
    assert not prof.run(["unset-secret", "FINNHUB_API_KEY"], environ=env)["settings"]["FINNHUB_API_KEY"]["set"]
    shown = prof.run(["show"], environ={**env, "FINNHUB_API_KEY": "x"})
    assert shown["settings"]["FINNHUB_API_KEY"]["source"] == "environment"


def test_empty_or_multiline_secret_rejected(env):
    assert not prof.run(["set-secret", "FINNHUB_API_KEY"], stdin="", environ=env)["ok"]
    assert not prof.run(["set-secret", "FINNHUB_API_KEY"], stdin="a\nb", environ=env)["ok"]


def test_data_dir_agrees_with_market_data(env):
    assert prof.data_dir(env) == market_core.data_dir(env)
    assert prof.data_dir({}) == market_core.data_dir({})


def test_example_profile_is_valid():
    example = json.loads((SKILL / "profile.example.json").read_text())
    prof.validate(example)
    assert example["screening_weights"] == prof.DEFAULT_WEIGHTS
