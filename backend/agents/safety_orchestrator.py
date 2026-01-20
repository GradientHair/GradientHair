"""Safety-aware multi-agent orchestrator for meeting interventions."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from agents.base_agent import AnalysisResult
from agents.moderator_agent import ModeratorAgent
from agents.participation_agent import ParticipationAgent
from agents.principle_agent import PrincipleAgent
from agents.topic_agent import TopicAgent
from models.meeting import Intervention, InterventionType, MeetingState, TranscriptEntry
from services.storage_service import StorageService
from openai import OpenAI
from pydantic import BaseModel, Field
from services.llm_validation import LLMStructuredOutputRunner, ValidationResult
from services.model_router import ModelRouter


@dataclass
class AgentError:
    agent_name: str
    error: str
    retryable: bool = True


@dataclass
class OrchestratorResult:
    intervention: Optional[Intervention]
    errors: list[AgentError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Blackboard:
    """File-backed shared state for multi-agent coordination."""

    def __init__(self, meeting_id: str):
        self.storage = StorageService()
        self.meeting_dir = self.storage.get_meeting_dir(meeting_id)
        self.path = self.meeting_dir / "blackboard.json"

    async def append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        data = await asyncio.to_thread(self._read)
        data.setdefault("events", [])
        data["events"].append({
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        })
        data["events"] = data["events"][-200:]
        await asyncio.to_thread(self._write, data)

    async def update_snapshot(self, snapshot: dict[str, Any]) -> None:
        data = await asyncio.to_thread(self._read)
        data["snapshot"] = snapshot
        data["updated_at"] = datetime.utcnow().isoformat()
        await asyncio.to_thread(self._write, data)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class CrashDetectionAgent:
    """Detects repeated failures and recommends recovery actions."""

    def __init__(self, max_errors: int = 3):
        self.max_errors = max_errors

    def analyze(self, errors: list[AgentError]) -> list[str]:
        if len(errors) >= self.max_errors:
            return ["에이전트 오류가 반복되어 자동 복구 절차를 실행합니다."]
        return []


class ErrorRecoveryAgent:
    """Attempts to recover from errors by reassigning to a fallback agent."""

    def __init__(self):
        self.fallback_agent = ModeratorAgent()

    async def recover(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry],
        errors: list[AgentError],
    ) -> Optional[Intervention]:
        if not errors:
            return None
        try:
            return await self.fallback_agent.analyze(state, recent_transcript)
        except Exception:
            return None


class SafetyCheckResponse(BaseModel):
    is_safe: bool = Field(...)
    safe_message: Optional[str] = None
    reasons: list[str] = Field(default_factory=list)


class SafetyCheckAgent:
    """Safety check using OpenAI API with structured output and retries."""

    def __init__(self):
        import os
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.max_retries = 2
        self.runner = None
        if self.client:
            choice = ModelRouter.select("fast", structured_output=True, api="chat")
            self.runner = LLMStructuredOutputRunner(
                client=self.client,
                model=choice.model,
                schema=SafetyCheckResponse,
                max_retries=self.max_retries,
                custom_validator=self._validate_response,
            )

    async def check(self, message: str) -> SafetyCheckResponse:
        if not message.strip():
            return SafetyCheckResponse(is_safe=True)
        if self.runner is None:
            return SafetyCheckResponse(is_safe=True)

        prompt = f"""당신은 회의 어시스턴트의 안전 검토자입니다.
메시지가 안전한지 판단하고, 안전하지 않다면 대체 메시지를 제안하세요.

메시지:
{message}

JSON 응답:
{{
  "is_safe": true/false,
  "safe_message": "안전한 대체 메시지 (필요 시)",
  "reasons": ["이유1", "이유2"]
}}
"""

        parsed = await asyncio.to_thread(self.runner.run, prompt)
        if parsed is None:
            return SafetyCheckResponse(
                is_safe=False,
                safe_message="안전 정책 위반 가능성이 있어 메시지를 조정합니다.",
                reasons=["fallback"],
            )
        return parsed

    def _validate_response(self, parsed: SafetyCheckResponse) -> ValidationResult:
        if not parsed.is_safe and not (parsed.safe_message or "").strip():
            return ValidationResult(ok=False, error="safe_message required when is_safe=false")
        return ValidationResult(ok=True, value=parsed)


class SafetyVerifierAgent:
    """Validates interventions and sanitizes unsafe responses."""

    def __init__(self, safety_check_agent: SafetyCheckAgent):
        self.max_length = 220
        self.safety_check_agent = safety_check_agent

    async def verify(self, intervention: Optional[Intervention]) -> Optional[Intervention]:
        if intervention is None:
            return None
        message = intervention.message or ""
        verdict = await self.safety_check_agent.check(message)
        if not verdict.is_safe:
            intervention.message = verdict.safe_message or "안전 정책 위반 가능성이 있어 메시지를 조정합니다."
            intervention.intervention_type = InterventionType.DECISION_STYLE
            message = intervention.message
        if self._is_unsafe(message):
            intervention.message = "대화가 안전 기준을 벗어날 수 있어 잠시 정리할게요."
            intervention.intervention_type = InterventionType.DECISION_STYLE
        if len(intervention.message) > self.max_length:
            intervention.message = intervention.message[: self.max_length].rstrip() + "…"
        return intervention

    def _is_unsafe(self, message: str) -> bool:
        unsafe_keywords = ["불법", "혐오", "폭력", "차별"]
        return any(k in message for k in unsafe_keywords)


class AdversarialReviewerAgent:
    """Adversarial check with strict criteria and limited turns."""

    def __init__(self, max_turns: int = 1):
        self.max_turns = max_turns

    def review(self, intervention: Intervention) -> tuple[bool, str]:
        if not intervention.message:
            return False, "개입 메시지가 비어 있습니다."
        if "source:" not in intervention.trigger_context:
            return False, "출처 정보가 없습니다."
        if len(intervention.message) < 6:
            return False, "메시지가 너무 짧습니다."
        return True, "승인"


class GroupChatCoordinator:
    """P2P group chat summary with clear goal and checkpoint."""

    def summarize(self, results: list[AnalysisResult]) -> str:
        if not results:
            return "요약: 개입 필요 없음."
        notes = [f"{r.agent_name}:{r.intervention_type}" for r in results if r.needs_intervention]
        return "요약: " + ", ".join(notes)


class PlannerAgent:
    """Plans which agents to run based on context."""

    def plan(self, state: MeetingState, recent_transcript: list[TranscriptEntry]) -> list[str]:
        if len(recent_transcript) < 2:
            return []
        plan = ["topic", "principle"]
        if len(state.participants) > 1:
            plan.append("participation")
        return plan


class SafetyOrchestrator:
    """Planner-Executor-Verifier orchestrator with safety checks."""

    def __init__(self):
        self.topic_agent = TopicAgent()
        self.principle_agent = PrincipleAgent()
        self.participation_agent = ParticipationAgent()
        self.planner = PlannerAgent()
        self.safety_check_agent = SafetyCheckAgent()
        self.verifier = SafetyVerifierAgent(self.safety_check_agent)
        self.crash_detector = CrashDetectionAgent()
        self.recovery_agent = ErrorRecoveryAgent()
        self.adversary = AdversarialReviewerAgent()
        self.group_chat = GroupChatCoordinator()
        self.last_intervention_time = 0
        self.min_intervention_interval = 15  # Base interval between interventions
        # Track recent interventions to prevent duplicates
        self.recent_interventions: list[dict] = []  # [{type, message_hash, timestamp}]
        self.max_recent_interventions = 10
        self.intervention_type_cooldowns = {
            "TOPIC_DRIFT": 60,  # 60 seconds cooldown for same type
            "PRINCIPLE_VIOLATION": 45,
            "PARTICIPATION_IMBALANCE": 90,
            "DECISION_STYLE": 60,
        }

    def _get_message_hash(self, message: str) -> str:
        """Create a simple hash of the message for deduplication."""
        import hashlib
        # Normalize message: lowercase, remove extra whitespace
        normalized = " ".join(message.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()[:8]

    def _is_duplicate_intervention(self, intervention_type: str, message: str, current_time: float) -> bool:
        """Check if this intervention is a duplicate of a recent one."""
        message_hash = self._get_message_hash(message)
        type_cooldown = self.intervention_type_cooldowns.get(intervention_type, 60)

        # Clean up old interventions
        self.recent_interventions = [
            r for r in self.recent_interventions
            if current_time - r["timestamp"] < max(self.intervention_type_cooldowns.values())
        ]

        for recent in self.recent_interventions:
            time_diff = current_time - recent["timestamp"]

            # Same message hash within cooldown period
            if recent["message_hash"] == message_hash and time_diff < type_cooldown:
                return True

            # Same intervention type within type-specific cooldown
            if recent["type"] == intervention_type and time_diff < type_cooldown:
                return True

        return False

    def _record_intervention(self, intervention_type: str, message: str, current_time: float) -> None:
        """Record an intervention for future duplicate checking."""
        self.recent_interventions.append({
            "type": intervention_type,
            "message_hash": self._get_message_hash(message),
            "timestamp": current_time,
        })
        # Keep only recent interventions
        if len(self.recent_interventions) > self.max_recent_interventions:
            self.recent_interventions = self.recent_interventions[-self.max_recent_interventions:]

    async def analyze(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry],
    ) -> OrchestratorResult:
        if len(recent_transcript) < 2:
            return OrchestratorResult(intervention=None)

        current_time = time.time()
        if current_time - self.last_intervention_time < self.min_intervention_interval:
            return OrchestratorResult(intervention=None)

        blackboard = Blackboard(state.meeting_id)
        await blackboard.update_snapshot({
            "participants": [p.name for p in state.participants],
            "recent_transcript": [t.text for t in recent_transcript[-5:]],
        })

        plan = self.planner.plan(state, recent_transcript)
        await blackboard.append_event("plan", {"agents": plan})

        results: list[AnalysisResult] = []
        errors: list[AgentError] = []

        tasks = []
        if "topic" in plan:
            tasks.append(self._run_agent("TopicAgent", self.topic_agent.analyze(state, recent_transcript)))
        if "principle" in plan:
            tasks.append(self._run_agent("PrincipleAgent", self.principle_agent.analyze(state, recent_transcript)))
        if "participation" in plan:
            tasks.append(self._run_agent("ParticipationAgent", self.participation_agent.analyze(state, recent_transcript)))

        if tasks:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for item in completed:
                if isinstance(item, AnalysisResult):
                    if item.needs_intervention:
                        results.append(item)
                elif isinstance(item, AgentError):
                    errors.append(item)

        await blackboard.append_event("checkpoint", {"summary": self.group_chat.summarize(results)})

        if not results and errors:
            recovery = await self.recovery_agent.recover(state, recent_transcript, errors)
            recovery = self._attach_sources(recovery, recent_transcript)
            verified = await self.verifier.verify(recovery)
            return OrchestratorResult(intervention=verified, errors=errors, warnings=self.crash_detector.analyze(errors))

        intervention = self._merge_interventions(results, recent_transcript)
        intervention = await self.verifier.verify(intervention)
        if intervention:
            # Check for duplicate intervention
            if self._is_duplicate_intervention(
                intervention.intervention_type.value,
                intervention.message,
                current_time
            ):
                return OrchestratorResult(
                    intervention=None,
                    errors=errors,
                    warnings=["Skipped duplicate intervention"],
                )

            approved, note = self.adversary.review(intervention)
            if not approved:
                intervention.message = f"검증 실패로 개입을 보류합니다. ({note})"
                intervention.intervention_type = InterventionType.DECISION_STYLE

        if intervention:
            self.last_intervention_time = current_time
            self._record_intervention(
                intervention.intervention_type.value,
                intervention.message,
                current_time
            )

        return OrchestratorResult(
            intervention=intervention,
            errors=errors,
            warnings=self.crash_detector.analyze(errors),
        )

    async def _run_agent(self, name: str, coroutine: Any) -> AnalysisResult | AgentError:
        try:
            return await coroutine
        except Exception as exc:
            return AgentError(agent_name=name, error=str(exc), retryable=True)

    def _merge_interventions(
        self,
        results: list[AnalysisResult],
        recent_transcript: list[TranscriptEntry],
    ) -> Optional[Intervention]:
        if not results:
            return None

        priority = {
            "PRINCIPLE_VIOLATION": 3,
            "TOPIC_DRIFT": 2,
            "PARTICIPATION_IMBALANCE": 1,
        }

        best = sorted(
            results,
            key=lambda r: (priority.get(r.intervention_type, 0), r.confidence),
            reverse=True,
        )[0]

        intervention = Intervention(
            id=f"int_{int(time.time())}",
            timestamp=datetime.utcnow().isoformat(),
            intervention_type=InterventionType(best.intervention_type),
            message=best.message,
            trigger_context=f"Detected by {best.agent_name}",
            violated_principle=best.violated_principle,
            parking_lot_item=best.parking_lot_item,
            suggested_speaker=best.suggested_speaker,
        )
        return self._attach_sources(intervention, recent_transcript)

    def _attach_sources(
        self,
        intervention: Optional[Intervention],
        recent_transcript: list[TranscriptEntry],
    ) -> Optional[Intervention]:
        if intervention is None or not recent_transcript:
            return intervention
        last = recent_transcript[-1]
        intervention.trigger_context = (
            f"{intervention.trigger_context} | source: {last.timestamp} {last.speaker}: {last.text}"
        )
        return intervention
