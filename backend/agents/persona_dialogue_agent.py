"""Persona Dialogue Agent - 페르소나 기반 회의 대화 생성."""
from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from models.meeting import MeetingState, TranscriptEntry
from services.llm_validation import LLMStructuredOutputRunner, ValidationResult
from services.model_router import ModelRouter


PERSONA_POOL = (
    "백엔드 엔지니어",
    "프론트 엔지니어",
    "UI/UX 엔지니어",
)

PERSONA_GUIDES = {
    "백엔드 엔지니어": "API 설계, 데이터 모델, 성능/확장성, 로그/모니터링에 초점을 맞춘다.",
    "프론트 엔지니어": "화면 플로우, 상태관리, 컴포넌트 구조, 사용자 입력 처리에 집중한다.",
    "UI/UX 엔지니어": "사용자 여정, 정보 구조, 접근성, 피드백 루프를 강조한다.",
}


class PersonaDialogueTurn(BaseModel):
    speaker: str = Field(...)
    text: str = Field(...)
    is_off_topic: bool = Field(...)
    is_agile_violation: bool = Field(...)


class PersonaDialogueResponse(BaseModel):
    utterances: list[PersonaDialogueTurn] = Field(default_factory=list)


@dataclass
class PersonaAssignment:
    name: str
    persona: str
    role: str


class PersonaDialogueAgent:
    """페르소나 기반 회의 대화를 생성하는 Agent."""

    def __init__(
        self,
        off_topic_rate: float = 0.12,
        agile_violation_rate: float = 0.1,
        max_retries: int = 2,
    ):
        self.off_topic_rate = max(0.0, min(1.0, off_topic_rate))
        self.agile_violation_rate = max(0.0, min(1.0, agile_violation_rate))
        self._assignments: dict[str, dict[str, str]] = {}
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.runner: Optional[LLMStructuredOutputRunner] = None
        if self.client:
            choice = ModelRouter.select("fast", structured_output=True, api="chat")
            self.runner = LLMStructuredOutputRunner(
                client=self.client,
                model=choice.model,
                schema=PersonaDialogueResponse,
                max_retries=max_retries,
                custom_validator=self._validate_response,
            )

    def assign_personas(
        self,
        state: MeetingState,
        rng: Optional[random.Random] = None,
    ) -> list[PersonaAssignment]:
        if not state.participants:
            return []
        rng = rng or random.Random()
        key = state.meeting_id or "default"
        existing = self._assignments.get(key, {})
        assignments: list[PersonaAssignment] = []
        for participant in state.participants:
            p_key = participant.id or participant.name
            persona = existing.get(p_key)
            if not persona:
                persona = rng.choice(PERSONA_POOL)
                existing[p_key] = persona
            assignments.append(PersonaAssignment(
                name=participant.name,
                persona=persona,
                role=participant.role,
            ))
        self._assignments[key] = existing
        return assignments

    def generate_dialogue(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry],
        turns: int = 3,
        seed: Optional[int] = None,
        stream: bool = True,
    ) -> list[PersonaDialogueTurn]:
        if not state.participants or turns < 1:
            return []

        if self.runner is None:
            raise RuntimeError("LLM runner unavailable. Set OPENAI_API_KEY to enable real mode.")

        rng = random.Random(seed)
        assignments = self.assign_personas(state, rng=rng)
        if not assignments:
            return []

        planned_turns = self._plan_turns(assignments, turns, rng)
        prompt = self._build_prompt(state, recent_transcript, planned_turns)
        parsed = self.runner.run(prompt, stream=stream)
        if parsed and parsed.utterances:
            return parsed.utterances
        raise RuntimeError("LLM generation failed. Check model access or prompt constraints.")

    def _plan_turns(
        self,
        assignments: list[PersonaAssignment],
        turns: int,
        rng: random.Random,
    ) -> list[PersonaDialogueTurn]:
        speakers = [a.name for a in assignments]
        rng.shuffle(speakers)
        planned: list[PersonaDialogueTurn] = []
        for idx in range(turns):
            speaker = speakers[idx % len(speakers)]
            planned.append(
                PersonaDialogueTurn(
                    speaker=speaker,
                    text="",
                    is_off_topic=rng.random() < self.off_topic_rate,
                    is_agile_violation=rng.random() < self.agile_violation_rate,
                )
            )
        return planned

    def _build_prompt(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry],
        planned_turns: list[PersonaDialogueTurn],
    ) -> str:
        agenda = state.agenda or "아젠다 없음"
        recent_text = "\n".join(
            f"{t.speaker}: {t.text}" for t in recent_transcript[-6:]
        ) or "최근 대화 없음"
        assignments = self.assign_personas(state)
        persona_lines = "\n".join(
            f"- {a.name} ({a.role}): {a.persona} — {PERSONA_GUIDES.get(a.persona, '')}"
            for a in assignments
        )
        planned_lines = "\n".join(
            f"- speaker={turn.speaker} | off_topic={turn.is_off_topic} | agile_violation={turn.is_agile_violation}"
            for turn in planned_turns
        )

        return f"""당신은 회의 발언을 생성하는 어시스턴트입니다.
참석자에게 페르소나를 부여한 뒤, 회의 내용을 바탕으로 업무 수행 방안을 논의하는 대화를 만듭니다.

아젠다:
{agenda}

최근 대화:
{recent_text}

페르소나:
{persona_lines}

생성해야 할 발언 계획:
{planned_lines}

규칙:
- 각 speaker에 대해 1개의 발언을 생성한다.
- off_topic=true인 경우, 아젠다와 무관한 가벼운 잡담을 포함한다.
- agile_violation=true인 경우, 해당 발언자가 본인 주장을 밀고 나가는 표현을 넣는다.
- 나머지 발언은 아젠다 기반으로 업무 수행 방법을 논의한다.
- 각 발언은 직전 발언을 이어 받아 한 단계씩 구체화한다.
- 같은 문장을 반복하지 않는다.
- 반드시 한국어 구어체로 자연스럽고 현실적인 톤으로 작성한다.
- 번호 매기기(예: 1), (1), ①)나 목록형 문장 대신, 대화체 한 문장/두 문장으로 말하듯이 작성한다.

JSON 응답:
{{
  "utterances": [
    {{
      "speaker": "이름",
      "text": "발언",
      "is_off_topic": true/false,
      "is_agile_violation": true/false
    }}
  ]
}}
"""

    def _validate_response(self, parsed: PersonaDialogueResponse) -> ValidationResult:
        if not parsed.utterances:
            return ValidationResult(ok=False, error="utterances required")
        return ValidationResult(ok=True, value=parsed)
