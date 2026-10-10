"""Optional env-file loading so --notify works on the Hermes fleet machine.

The repo never contains secrets. When TELEGRAM_* vars are not already in the
environment, the CLI loads the first existing candidates (set-if-missing —
real environment variables always win):

  $KPR_ENV_FILE  (explicit override)
  ~/.hermes/profiles/scout/.env
  ~/.hermes/.env

Set KPR_SKIP_ENV_FILE=1 to disable entirely (e.g. CI).
"""
from __future__ import annotations

import os
from pathlib import Path

CANDIDATES = (
    "~/.hermes/profiles/scout/.env",
    "~/.hermes/.env",
)


def apply_env_file(path) -> int:
    """Set KEY=VALUE pairs from a dotenv-style file without overriding
    existing environment variables. Returns how many were set."""
    applied = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            if text.startswith("export "):
                text = text[len("export "):]
            key, value = text.split("=", 1)
            key = key.strip()
            if not key.replace("_", "").isalnum() or key[0].isdigit():
                continue
            value = value.strip().strip('"').strip("'")
            if not value:
                continue
            if key not in os.environ:
                os.environ[key] = value
                applied += 1
    return applied


def load_env() -> str:
    """Load the first existing candidate env files (gaps only). Returns the
    file used, or '' when none applied."""
    if os.environ.get("KPR_SKIP_ENV_FILE") == "1":
        return ""
    candidates = []
    explicit = os.environ.get("KPR_ENV_FILE")
    if explicit:
        candidates.append(explicit)
    candidates.extend(CANDIDATES)
    used = []
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file():
            if apply_env_file(path):
                used.append(str(path))
            if explicit:  # explicit file is authoritative enough; stop there
                break
    return used[0] if used else ""
