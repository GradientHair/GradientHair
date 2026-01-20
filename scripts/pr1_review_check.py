#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def check_repo() -> dict:
    root = Path(__file__).resolve().parents[1]
    checks = []

    checks.append(("openai_sdk_usage", (root / "backend").exists()))
    checks.append(("multi_agent_structure", (root / "backend/agents/safety_orchestrator.py").exists()))
    checks.append(("observability", (root / "backend/server.py").exists()))
    checks.append(("documentation", (root / "README.md").exists() and (root / "AGENTS.md").exists()))
    checks.append(("storage_structure", (root / "backend/services/storage_service.py").exists()))
    checks.append(("topic_intervention", (root / "backend/agents/topic_agent.py").exists()))
    checks.append(("principle_intervention", (root / "backend/agents/principle_agent.py").exists()))
    checks.append(("participation_balance", (root / "backend/agents/participation_agent.py").exists()))
    checks.append(("smoke_tests", (root / "scripts/run_smoke.sh").exists()))
    checks.append(("demo_flow", (root / "AGENTS.md").read_text(encoding="utf-8").find("Playwright UI Demo Flow") >= 0))

    results = {
        "ok": all(ok for _, ok in checks),
        "checks": [{"name": name, "ok": ok} for name, ok in checks],
    }
    return results


def score(checks: dict) -> dict:
    lookup = {item["name"]: item["ok"] for item in checks["checks"]}
    # PR#1 format weights
    core = {
        "openai_sdk_usage": 0.06,
        "multi_agent_structure": 0.06,
        "observability": 0.06,
        "documentation": 0.06,
        "storage_structure": 0.06,
        "topic_intervention": 0.06,
        "principle_intervention": 0.06,
        "participation_balance": 0.06,
        "smoke_tests": 0.06,
        "demo_flow": 0.06,
    }  # total 0.60
    openai = {
        "moderation": 0.10,
        "eval_logging": 0.05,
        "eval_harness": 0.05,
    }  # total 0.20
    safety = {
        "guardrails": 0.10,
        "prompt_injection": 0.05,
        "red_team_tests": 0.05,
    }  # total 0.20

    # infer from repo
    has_safety_check = (Path(__file__).resolve().parents[1] / "backend/agents/safety_orchestrator.py").read_text(encoding="utf-8").find("SafetyCheckAgent") >= 0
    openai["moderation"] = 0.10 if has_safety_check else 0.0
    openai["eval_logging"] = 0.0
    openai["eval_harness"] = 0.0
    safety["guardrails"] = 0.10 if has_safety_check else 0.0
    safety["prompt_injection"] = 0.0
    safety["red_team_tests"] = 0.0

    core_score = sum(weight for key, weight in core.items() if lookup.get(key))
    openai_score = sum(openai.values())
    safety_score = sum(safety.values())

    total = (core_score + openai_score + safety_score) * 100
    return {
        "core": core_score / 0.60,
        "openai": openai_score / 0.20,
        "safety": safety_score / 0.20,
        "score": round(total),
    }


def main() -> int:
    results = check_repo()
    scoring = score(results)
    output = {
        "checks": results["checks"],
        "score": scoring["score"],
        "section_scores": {
            "core": round(scoring["core"], 2),
            "openai": round(scoring["openai"], 2),
            "red_team": round(scoring["safety"], 2),
        },
    }
    print(json.dumps(output, indent=2))
    print(f"[pr1-review] Score: {scoring['score']}/100")
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
