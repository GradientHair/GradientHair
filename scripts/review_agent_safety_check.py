#!/usr/bin/env python3
import json
import sys
import urllib.request
from pathlib import Path


README_URL = "https://raw.githubusercontent.com/GradientHair/GradientHair/review-agent-safety/README.md"


def fetch_readme() -> str:
    try:
        with urllib.request.urlopen(README_URL, timeout=10) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"[review-check] Failed to fetch README: {exc}")
        return ""


def file_contains(path: Path, needle: str) -> bool:
    if not path.exists():
        return False
    try:
        return needle in path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False


def check_repo() -> dict:
    root = Path(__file__).resolve().parents[1]
    checks = []

    safety_orchestrator = root / "backend/agents/safety_orchestrator.py"
    review_agent = root / "backend/agents/review_agent.py"
    principle_agent = root / "backend/agents/principle_agent.py"
    topic_agent = root / "backend/agents/topic_agent.py"
    server = root / "backend/server.py"
    smoke_script = root / "scripts/run_smoke.sh"
    llm_validation = root / "backend/services/llm_validation.py"

    checks.append(("multi_agent_orchestrator", safety_orchestrator.exists()))
    checks.append(("review_agent", review_agent.exists()))
    checks.append(("crash_detection_agent", file_contains(safety_orchestrator, "CrashDetectionAgent")))
    checks.append(("error_recovery_agent", file_contains(safety_orchestrator, "ErrorRecoveryAgent")))
    checks.append(("adversarial_review", file_contains(safety_orchestrator, "AdversarialReviewerAgent")))
    checks.append(("p2p_group_chat", file_contains(safety_orchestrator, "GroupChatCoordinator")))
    checks.append(("blackboard_bot", file_contains(safety_orchestrator, "Blackboard")))
    checks.append(("planner_executor_verifier", file_contains(safety_orchestrator, "PlannerAgent") and file_contains(safety_orchestrator, "SafetyVerifierAgent")))
    checks.append(("schema_validation_principle", file_contains(principle_agent, "pydantic")))
    checks.append(("schema_validation_topic", file_contains(topic_agent, "pydantic")))
    checks.append(("schema_validation_review", file_contains(review_agent, "pydantic")))
    checks.append(("validation_pipeline", llm_validation.exists() and file_contains(llm_validation, "LLMStructuredOutputRunner")))
    checks.append(("dspy_pipeline", file_contains(llm_validation, "DSPyValidator")))
    checks.append(("evidence_citations", file_contains(review_agent, "evidence")))
    checks.append(("chunking_indexing", file_contains(review_agent, "_build_transcript_index")))
    checks.append(("openai_safety_check", file_contains(safety_orchestrator, "SafetyCheckAgent")))
    checks.append(("private_feedback", file_contains(review_agent, "ParticipantFeedbackAgent")))
    checks.append(("event_driven_runtime", file_contains(server, "websocket_endpoint")))
    checks.append(("orchestrator_wired", file_contains(server, "SafetyOrchestrator")))
    checks.append(("single_command_demo", smoke_script.exists()))
    checks.append(("critic_refiner", file_contains(safety_orchestrator, "검증 실패")))

    results = {
        "ok": all(ok for _, ok in checks),
        "checks": [{"name": name, "ok": ok} for name, ok in checks],
    }
    return results


def score_repo(checks: dict) -> dict:
    lookup = {item["name"]: item["ok"] for item in checks["checks"]}
    rubric = [
        ("supervisor_worker_event", 15, lookup.get("multi_agent_orchestrator") and lookup.get("event_driven_runtime") and lookup.get("orchestrator_wired")),
        ("crash_and_recovery", 10, lookup.get("crash_detection_agent") and lookup.get("error_recovery_agent")),
        ("schema_validation", 10, lookup.get("schema_validation_principle") and lookup.get("schema_validation_topic") and lookup.get("schema_validation_review")),
        ("validation_pipeline", 10, lookup.get("validation_pipeline")),
        ("dspy_pipeline", 5, lookup.get("dspy_pipeline")),
        ("openai_safety_check", 10, lookup.get("openai_safety_check")),
        ("evidence_citations", 10, lookup.get("evidence_citations")),
        ("chunking_indexing", 5, lookup.get("chunking_indexing")),
        ("blackboard_bot", 5, lookup.get("blackboard_bot")),
        ("p2p_group_chat", 5, lookup.get("p2p_group_chat")),
        ("agent_set", 10, lookup.get("review_agent") and lookup.get("multi_agent_orchestrator")),
        ("single_command_demo", 10, lookup.get("single_command_demo")),
        ("private_feedback", 10, lookup.get("private_feedback")),
        ("critic_refiner_loop", 10, lookup.get("adversarial_review") and lookup.get("critic_refiner")),
    ]

    total = 0
    items = []
    for name, weight, ok in rubric:
        score = weight if ok else 0
        total += score
        items.append({"name": name, "weight": weight, "ok": bool(ok), "score": score})

    return {"score": total, "max_score": sum(w for _, w, _ in rubric), "rubric": items}


def main() -> int:
    readme = fetch_readme()
    if readme:
        print("[review-check] Loaded review-agent-safety README.")
    else:
        print("[review-check] README not available; proceeding with local checks only.")

    results = check_repo()
    scoring = score_repo(results)
    output = {
        "readme_loaded": bool(readme),
        "score": scoring["score"],
        "max_score": scoring["max_score"],
        "checks": results["checks"],
        "rubric": scoring["rubric"],
    }
    print(json.dumps(output, indent=2))

    if not results["ok"]:
        print("[review-check] One or more checks failed.")
        return 1

    print(f"[review-check] Score: {scoring['score']}/{scoring['max_score']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
