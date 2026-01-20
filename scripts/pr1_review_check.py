#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    weight: float = 0.0
    section: str = "core"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _exists(path: Path) -> bool:
    return path.exists()


def _contains_any(path: Path, patterns: Iterable[str]) -> bool:
    text = _read_text(path)
    if not text:
        return False
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _glob_exists(pattern: str) -> bool:
    return any(ROOT.glob(pattern))


def _check_openai_sdk_usage() -> CheckResult:
    pyproject = ROOT / "backend/pyproject.toml"
    requirements = ROOT / "backend/requirements.txt"
    uv_lock = ROOT / "backend/uv.lock"
    found = (
        _contains_any(pyproject, [r"openai"])
        or _contains_any(requirements, [r"openai"])
        or _contains_any(uv_lock, [r"openai"])
    )
    detail = "openai dependency found" if found else "openai dependency not found"
    return CheckResult("openai_sdk_usage", found, detail, weight=0.06, section="core")


def _check_multi_agent_structure() -> CheckResult:
    agents_dir = ROOT / "backend/agents"
    orchestrator = ROOT / "backend/agents/safety_orchestrator.py"
    ok = agents_dir.exists() and orchestrator.exists()
    detail = "agents directory and safety_orchestrator.py present" if ok else "agents structure missing"
    return CheckResult("multi_agent_structure", ok, detail, weight=0.06, section="core")


def _check_observability() -> CheckResult:
    server = ROOT / "backend/server.py"
    ok = _contains_any(server, [r"logging", r"logger\.", r"structlog"])
    detail = "logging hooks detected in server" if ok else "logging hooks not detected in server"
    return CheckResult("observability", ok, detail, weight=0.06, section="core")


def _check_documentation() -> CheckResult:
    readme = ROOT / "README.md"
    agents = ROOT / "AGENTS.md"
    ok = readme.exists() and agents.exists()
    detail = "README.md and AGENTS.md present" if ok else "README.md or AGENTS.md missing"
    return CheckResult("documentation", ok, detail, weight=0.06, section="core")


def _check_storage_structure() -> CheckResult:
    storage = ROOT / "backend/services/storage_service.py"
    ok = storage.exists()
    detail = "storage service present" if ok else "storage service missing"
    return CheckResult("storage_structure", ok, detail, weight=0.06, section="core")


def _check_topic_intervention() -> CheckResult:
    topic_agent = ROOT / "backend/agents/topic_agent.py"
    ok = topic_agent.exists()
    detail = "topic agent present" if ok else "topic agent missing"
    return CheckResult("topic_intervention", ok, detail, weight=0.06, section="core")


def _check_principle_intervention() -> CheckResult:
    principle_agent = ROOT / "backend/agents/principle_agent.py"
    ok = principle_agent.exists()
    detail = "principle agent present" if ok else "principle agent missing"
    return CheckResult("principle_intervention", ok, detail, weight=0.06, section="core")


def _check_participation_balance() -> CheckResult:
    participation_agent = ROOT / "backend/agents/participation_agent.py"
    ok = participation_agent.exists()
    detail = "participation agent present" if ok else "participation agent missing"
    return CheckResult("participation_balance", ok, detail, weight=0.06, section="core")


def _check_smoke_tests() -> CheckResult:
    smoke = ROOT / "scripts/run_smoke.sh"
    ok = smoke.exists()
    detail = "scripts/run_smoke.sh present" if ok else "scripts/run_smoke.sh missing"
    return CheckResult("smoke_tests", ok, detail, weight=0.06, section="core")


def _check_demo_flow() -> CheckResult:
    agents = ROOT / "AGENTS.md"
    ok = _contains_any(agents, [r"Playwright UI Demo Flow"])
    detail = "Playwright demo flow documented" if ok else "Playwright demo flow not documented"
    return CheckResult("demo_flow", ok, detail, weight=0.06, section="core")


def _check_moderation() -> CheckResult:
    server = ROOT / "backend/server.py"
    uses_moderation = _contains_any(server, [r"moderation", r"omni-moderation", r"content_filter"])
    detail = "moderation API usage detected" if uses_moderation else "moderation API usage not detected"
    return CheckResult("moderation", uses_moderation, detail, weight=0.10, section="openai")


def _check_eval_logging() -> CheckResult:
    ok = _glob_exists("**/eval*.py") or _glob_exists("**/evaluation*.py")
    detail = "eval logging artifacts detected" if ok else "eval logging artifacts not detected"
    return CheckResult("eval_logging", ok, detail, weight=0.05, section="openai")


def _check_eval_harness() -> CheckResult:
    ok = _glob_exists("**/evals/**") or _glob_exists("**/evaluation/**")
    detail = "eval harness directory detected" if ok else "eval harness directory not detected"
    return CheckResult("eval_harness", ok, detail, weight=0.05, section="openai")


def _check_guardrails() -> CheckResult:
    safety = ROOT / "backend/agents/safety_orchestrator.py"
    ok = _contains_any(safety, [r"SafetyCheckAgent", r"guardrail", r"safety check"])
    detail = "safety guardrails detected" if ok else "safety guardrails not detected"
    return CheckResult("guardrails", ok, detail, weight=0.10, section="red_team")


def _check_prompt_injection() -> CheckResult:
    files = [
        ROOT / "backend/agents",
        ROOT / "backend/services",
        ROOT / "docs",
        ROOT / "README.md",
    ]
    patterns = [r"prompt injection", r"jailbreak", r"system prompt hardening"]
    ok = any(
        _contains_any(path, patterns)
        if path.is_file()
        else any(_contains_any(p, patterns) for p in path.rglob("*.md"))
        or any(_contains_any(p, patterns) for p in path.rglob("*.py"))
        for path in files
        if path.exists()
    )
    detail = "prompt injection mitigation noted" if ok else "prompt injection mitigation not found"
    return CheckResult("prompt_injection", ok, detail, weight=0.05, section="red_team")


def _check_red_team_tests() -> CheckResult:
    ok = _glob_exists("**/red_team*") or _glob_exists("**/redteam*")
    detail = "red-team artifacts detected" if ok else "red-team artifacts not detected"
    return CheckResult("red_team_tests", ok, detail, weight=0.05, section="red_team")


def run_checks() -> list[CheckResult]:
    return [
        _check_openai_sdk_usage(),
        _check_multi_agent_structure(),
        _check_observability(),
        _check_documentation(),
        _check_storage_structure(),
        _check_topic_intervention(),
        _check_principle_intervention(),
        _check_participation_balance(),
        _check_smoke_tests(),
        _check_demo_flow(),
        _check_moderation(),
        _check_eval_logging(),
        _check_eval_harness(),
        _check_guardrails(),
        _check_prompt_injection(),
        _check_red_team_tests(),
    ]


def score(checks: list[CheckResult]) -> dict:
    totals = {"core": 0.0, "openai": 0.0, "red_team": 0.0}
    maximums = {"core": 0.0, "openai": 0.0, "red_team": 0.0}
    for check in checks:
        maximums[check.section] += check.weight
        if check.ok:
            totals[check.section] += check.weight

    def norm(section: str) -> float:
        if maximums[section] == 0:
            return 0.0
        return round(totals[section] / maximums[section], 2)

    total_score = round(sum(totals.values()) * 100)
    return {
        "score": total_score,
        "section_scores": {
            "core": norm("core"),
            "openai": norm("openai"),
            "red_team": norm("red_team"),
        },
    }


def main() -> int:
    checks = run_checks()
    scoring = score(checks)
    output = {
        "checks": [
            {
                "name": check.name,
                "ok": check.ok,
                "detail": check.detail,
                "weight": check.weight,
                "section": check.section,
            }
            for check in checks
        ],
        "score": scoring["score"],
        "section_scores": scoring["section_scores"],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"[pr1-review] Score: {scoring['score']}/100")

    core_ok = all(check.ok for check in checks if check.section == "core")
    return 0 if core_ok else 1


if __name__ == "__main__":
    sys.exit(main())
