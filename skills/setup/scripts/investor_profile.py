# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Manage the Investor Profile and settings in the data dir (ADR 0004).

    uv run --script investor_profile.py show
    uv run --script investor_profile.py init --language de
    uv run --script investor_profile.py set explanation_depth=beginner risk_tolerance=medium
    uv run --script investor_profile.py set weights.fundamentals=40 weights.technical=5
    echo "<value>" | uv run --script investor_profile.py set-secret FINNHUB_API_KEY
    uv run --script investor_profile.py unset-secret FINNHUB_API_KEY

Every command prints one JSON object. Secret values are never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR_ENV = "FINANCIAL_SUPPORT_HOME"
PROFILE_FILE = "profile.json"
ENV_FILE = ".env"
SCHEMA_VERSION = 1

CHOICES = {
    "explanation_depth": ("beginner", "advanced"),
    "default_horizon": ("short-term", "medium-term"),
    "risk_tolerance": ("low", "medium", "high"),
}
WEIGHT_KEYS = ("fundamentals", "valuation", "dividend", "thematic", "technical")
DEFAULT_WEIGHTS = {"fundamentals": 30, "valuation": 25, "dividend": 15, "thematic": 15, "technical": 15}
SECRETS = {
    "FINNHUB_API_KEY": "Free Finnhub key for more reliable earnings dates (https://finnhub.io/register)",
    "SEC_USER_AGENT": "Name and e-mail sent to SEC EDGAR with each request, e.g. 'Jane Doe jane@example.com'",
}


class ProfileError(ValueError):
    pass


# --- paths and files ---------------------------------------------------------------------------


def data_dir(environ: dict[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    override = env.get(DATA_DIR_ENV)
    return Path(override).expanduser() if override else Path.home() / ".financial-support"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_profile(language: str) -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "language": language,
        "explanation_depth": "beginner",
        "default_horizon": "medium-term",
        "risk_tolerance": "medium",
        "screening_weights": dict(DEFAULT_WEIGHTS),
        "updated_at": _now(),
    }


def load_profile(root: Path) -> dict[str, Any] | None:
    path = root / PROFILE_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def save_profile(root: Path, profile: dict[str, Any]) -> None:
    validate(profile)
    root.mkdir(parents=True, exist_ok=True)
    profile["updated_at"] = _now()
    tmp = root / (PROFILE_FILE + ".tmp")
    tmp.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(root / PROFILE_FILE)


def read_env(root: Path) -> dict[str, str]:
    path = root / ENV_FILE
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def write_env(root: Path, values: dict[str, str]) -> None:
    """Rewrite .env with owner-only permissions (it holds API keys)."""
    root.mkdir(parents=True, exist_ok=True)
    path = root / ENV_FILE
    lines = ["# financial-support settings, written by the setup skill. Keep this file private."]
    lines += [f'{k}="{v}"' for k, v in sorted(values.items())]
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


# --- validation and updates --------------------------------------------------------------------


def validate(profile: dict[str, Any]) -> None:
    lang = profile.get("language")
    if not isinstance(lang, str) or not (2 <= len(lang) <= 8) or not lang.replace("-", "").isalpha():
        raise ProfileError(f"language must be a language code like 'de' or 'en', got {lang!r}")
    for key, allowed in CHOICES.items():
        if profile.get(key) not in allowed:
            raise ProfileError(f"{key} must be one of {', '.join(allowed)}, got {profile.get(key)!r}")
    weights = profile.get("screening_weights")
    if not isinstance(weights, dict) or set(weights) != set(WEIGHT_KEYS):
        raise ProfileError(f"screening_weights must have exactly: {', '.join(WEIGHT_KEYS)}")
    for key, value in weights.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ProfileError(f"weight {key} must be a whole number >= 0, got {value!r}")
    if sum(weights.values()) != 100:
        raise ProfileError(f"screening weights must add up to 100, they add up to {sum(weights.values())}")


def apply_updates(profile: dict[str, Any], assignments: list[str]) -> dict[str, Any]:
    """Apply key=value assignments. Weights are given as weights.<name>=<int>.

    If only some weights change, the result must still add up to 100. Otherwise this is an error,
    so the investor decides how to rebalance rather than the script silently doing it.
    """
    updated = json.loads(json.dumps(profile))
    for item in assignments:
        if "=" not in item:
            raise ProfileError(f"expected key=value, got {item!r}")
        key, value = (part.strip() for part in item.split("=", 1))
        if key.startswith("weights."):
            name = key.removeprefix("weights.")
            if name not in WEIGHT_KEYS:
                raise ProfileError(f"unknown weight {name!r}; known: {', '.join(WEIGHT_KEYS)}")
            try:
                updated["screening_weights"][name] = int(value)
            except ValueError:
                raise ProfileError(f"weight {name} must be a whole number, got {value!r}") from None
        elif key in CHOICES or key == "language":
            updated[key] = value.lower()
        else:
            raise ProfileError(f"unknown setting {key!r}")
    validate(updated)
    return updated


def secret_status(root: Path, environ: dict[str, str] | None = None) -> dict[str, dict[str, Any]]:
    """Which settings are set and where; never the values themselves."""
    env = os.environ if environ is None else environ
    file_values = read_env(root)
    out = {}
    for name, purpose in SECRETS.items():
        where = "environment" if env.get(name) else ("file" if file_values.get(name) else None)
        out[name] = {"set": where is not None, "source": where, "purpose": purpose}
    return out


# --- commands ----------------------------------------------------------------------------------


def run(argv: list[str], stdin: str | None = None, environ: dict[str, str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="investor_profile.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show")
    p = sub.add_parser("init")
    p.add_argument("--language", required=True)
    p.add_argument("--force", action="store_true", help="Overwrite an existing profile with defaults")
    p = sub.add_parser("set")
    p.add_argument("assignments", nargs="+")
    p = sub.add_parser("set-secret")
    p.add_argument("name", choices=sorted(SECRETS))
    p = sub.add_parser("unset-secret")
    p.add_argument("name", choices=sorted(SECRETS))
    args = parser.parse_args(argv)

    root = data_dir(environ)
    result: dict[str, Any] = {"command": args.command, "data_dir": str(root), "ok": True, "error": None}
    try:
        if args.command == "init":
            existing = load_profile(root)
            if existing and not args.force:
                result["created"] = False
                result["profile"] = existing
            else:
                profile = default_profile(args.language.lower())
                save_profile(root, profile)
                result["created"] = True
                result["profile"] = profile
        elif args.command == "set":
            profile = load_profile(root)
            if profile is None:
                raise ProfileError("no Investor Profile yet; run init first")
            profile = apply_updates(profile, args.assignments)
            save_profile(root, profile)
            result["profile"] = profile
        elif args.command == "set-secret":
            value = (stdin or "").strip()
            if not value:
                raise ProfileError("no value given on stdin")
            if "\n" in value or '"' in value:
                raise ProfileError("value must be a single line without double quotes")
            values = read_env(root)
            values[args.name] = value
            write_env(root, values)
        elif args.command == "unset-secret":
            values = read_env(root)
            values.pop(args.name, None)
            write_env(root, values)
        if args.command == "show":
            result["profile"] = load_profile(root)
        result["settings"] = secret_status(root, environ)
    except (ProfileError, json.JSONDecodeError) as exc:
        result.update(ok=False, error=str(exc))
    return result


def main() -> int:
    argv = sys.argv[1:]
    stdin = sys.stdin.read() if argv[:1] == ["set-secret"] and not sys.stdin.isatty() else None
    result = run(argv, stdin)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
