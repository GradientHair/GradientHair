from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.models import DemoScript, DemoScriptSummary


def _normalize_scripts(raw: object) -> list[dict]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "scripts" in raw:
        return raw["scripts"]
    if isinstance(raw, dict):
        return [raw]
    raise ValueError("Invalid demo script format")


def load_scripts(path: str | Path) -> list[DemoScript]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Demo script not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    scripts = _normalize_scripts(raw)
    return [DemoScript.model_validate(script) for script in scripts]


def get_script(path: str | Path, script_id: str | None) -> DemoScript:
    scripts = load_scripts(path)
    if not script_id:
        return scripts[0]
    for script in scripts:
        if script.id == script_id:
            return script
    raise ValueError(f"Unknown demo_script_id: {script_id}")


def summarize_scripts(path: str | Path) -> list[DemoScriptSummary]:
    scripts = load_scripts(path)
    summaries: list[DemoScriptSummary] = []
    for script in scripts:
        summaries.append(
            DemoScriptSummary(
                id=script.id,
                title=script.title,
                agenda=script.agenda,
                participants=script.participants,
                description=script.description,
            )
        )
    return summaries
