"""Lightweight .env support for backend runtime secrets."""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BACKEND_DIR / ".env"


def _parse_env_line(line: str) -> tuple[str, str] | None:
    text = line.strip().lstrip("\ufeff")
    if not text or text.startswith("#"):
        return None
    if text.startswith("export "):
        text = text[7:].strip()
    if "=" not in text:
        return None

    key, value = text.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value


def load_env_file(path: Path = ENV_PATH, override: bool = False) -> None:
    """Load KEY=VALUE pairs from backend/.env into os.environ."""
    if not path.exists():
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for line in lines:
        parsed = _parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        if override or not os.getenv(key):
            os.environ[key] = value


def update_env_file(updates: dict[str, str], path: Path = ENV_PATH) -> None:
    """Persist selected runtime secrets to backend/.env."""
    existing_lines: list[str] = []
    if path.exists():
        existing_lines = path.read_text(encoding="utf-8").splitlines()

    applied: set[str] = set()
    output: list[str] = []

    for line in existing_lines:
        parsed = _parse_env_line(line)
        if parsed is None:
            output.append(line)
            continue

        key, _ = parsed
        if key in updates:
            output.append(f"{key}={updates[key]}")
            applied.add(key)
        else:
            output.append(line)

    for key, value in updates.items():
        if key not in applied:
            output.append(f"{key}={value}")

    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")

    for key, value in updates.items():
        os.environ[key] = value
