"""Persona Dialogue Agent - 페르소나 기반 회의 대화 생성."""

from __future__ import annotations

import os
import random
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable

from openai import OpenAI
from pydantic import BaseModel, Field

from models.meeting import MeetingState, TranscriptEntry
from services.model_router import ModelRouter
from i18n import pick, is_english


PERSONA_POOL = {
    "ko": (
        "백엔드 엔지니어",
        "프론트 엔지니어",
        "UI/UX 엔지니어",
    ),
    "en": (
        "Backend engineer",
        "Frontend engineer",
        "UI/UX engineer",
    ),
}

PERSONA_GUIDES = {
    "ko": {
        "백엔드 엔지니어": "API 설계, 데이터 모델, 성능/확장성, 로그/모니터링에 초점을 맞춘다.",
        "프론트 엔지니어": "화면 플로우, 상태관리, 컴포넌트 구조, 사용자 입력 처리에 집중한다.",
        "UI/UX 엔지니어": "사용자 여정, 정보 구조, 접근성, 피드백 루프를 강조한다.",
    },
    "en": {
        "Backend engineer": "Focus on API design, data models, scalability/performance, and logging/monitoring.",
        "Frontend engineer": "Focus on user flows, state management, component structure, and input handling.",
        "UI/UX engineer": "Emphasize user journey, information architecture, accessibility, and feedback loops.",
    },
}


class PersonaDialogueTurn(BaseModel):
    speaker: str = Field(...)
    text: str = Field(...)
    is_off_topic: bool = Field(...)
    is_agile_violation: bool = Field(...)


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
        stream: bool = True,
    ):
        self.off_topic_rate = max(0.0, min(1.0, off_topic_rate))
        self.agile_violation_rate = max(0.0, min(1.0, agile_violation_rate))
        self.stream = stream
        self._assignments: dict[str, dict[str, str]] = {}
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.model: Optional[str] = None
        if self.client:
            choice = ModelRouter.select("fast", structured_output=False, api="chat")
            self.model = choice.model

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
                pool = PERSONA_POOL["en"] if is_english() else PERSONA_POOL["ko"]
                persona = rng.choice(pool)
                existing[p_key] = persona
            assignments.append(
                PersonaAssignment(
                    name=participant.name,
                    persona=persona,
                    role=participant.role,
                )
            )
        self._assignments[key] = existing
        return assignments

    def generate_dialogue(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry],
        turns: int = 3,
        seed: Optional[int] = None,
        turn_offset: int = 0,
        stream: Optional[bool] = None,
        stream_callback: Optional[Callable[[str, str], None]] = None,
    ) -> list[PersonaDialogueTurn]:
        if not state.participants or turns < 1:
            return []

        if not self.client or not self.model:
            raise RuntimeError("LLM unavailable. Set OPENAI_API_KEY to enable.")

        rng = random.Random(seed)
        assignments = self.assign_personas(state, rng=rng)
        if not assignments:
            return []

        use_stream = self.stream if stream is None else stream
        all_utterances: list[PersonaDialogueTurn] = []

        # 각 턴마다 1개씩 발언 생성
        for turn_idx in range(turns):
            # 현재 턴의 발언 계획 (1개만)
            planned_turn = self._plan_single_turn(assignments, turn_offset + turn_idx, rng)

            # 최근 대화에 이전 생성된 발언들 포함
            # Build a temporary transcript that mimics real entries to keep the prompt format consistent
            current_transcript = recent_transcript + [
                TranscriptEntry(
                    id=f"tmp_{uuid.uuid4().hex[:8]}",
                    speaker=utt.speaker,
                    text=utt.text,
                    timestamp=datetime.utcnow().isoformat(),
                )
                for utt in all_utterances
            ]

            prompt = self._build_prompt(state, current_transcript, planned_turn)

            if use_stream:
                print(f"\n{'='*60}")
                print(f"Turn {turn_idx + 1}/{turns} - Speaker: {planned_turn.speaker}")
                print(f"{'='*60}")

            text = self._generate_utterance_text(
                prompt=prompt,
                stream=use_stream,
                print_stream=use_stream,
                stream_callback=stream_callback,
                speaker=planned_turn.speaker,
            )
            if not text:
                raise RuntimeError(f"LLM generation failed at turn {turn_idx + 1}")

            clean_text = self._strip_speaker_prefix(text)
            clean_text = self._remove_brackets(clean_text)

            utterance = PersonaDialogueTurn(
                speaker=planned_turn.speaker,
                text=clean_text,
                is_off_topic=planned_turn.is_off_topic,
                is_agile_violation=planned_turn.is_agile_violation,
            )
            all_utterances.append(utterance)

        return all_utterances

    def _plan_single_turn(
        self,
        assignments: list[PersonaAssignment],
        turn_idx: int,
        rng: random.Random,
    ) -> PersonaDialogueTurn:
        """단일 턴의 발언 계획 생성"""
        speakers = [a.name for a in assignments]
        speaker = speakers[turn_idx % len(speakers)]

        return PersonaDialogueTurn(
            speaker=speaker,
            text="",
            is_off_topic=rng.random() < self.off_topic_rate,
            is_agile_violation=rng.random() < self.agile_violation_rate,
        )

    def _build_prompt(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry],
        planned_turn: PersonaDialogueTurn,
    ) -> str:
        agenda = state.agenda or pick("아젠다 없음", "No agenda")
        recent_text = (
            "\n".join(f"{t.speaker}: {t.text}" for t in recent_transcript[-8:])
            or pick("최근 대화 없음", "No recent conversation")
        )
        assignments = self.assign_personas(state)
        guides = PERSONA_GUIDES["en"] if is_english() else PERSONA_GUIDES["ko"]
        persona_lines = "\n".join(
            f"- {a.name} ({a.role}): {a.persona} — {guides.get(a.persona, '')}"
            for a in assignments
        )

        return pick(
            f"""당신은 회의 발언을 생성하는 어시스턴트입니다.
참석자에게 페르소나를 부여한 뒤, 회의 내용을 바탕으로 업무 수행 방안을 논의하는 대화를 만듭니다.

아젠다:
{agenda}

최근 대화:
{recent_text}

페르소나:
{persona_lines}

다음 발언자 정보:
- speaker: {planned_turn.speaker}
- off_topic: {planned_turn.is_off_topic}
- agile_violation: {planned_turn.is_agile_violation}

규칙:
- {planned_turn.speaker}의 발언 **1개만** 생성합니다.
- off_topic=true인 경우, 아젠다와 무관한 가벼운 잡담을 포함합니다.
- agile_violation=true인 경우, 해당 발언자가 본인 주장을 밀고 나가는 표현을 넣습니다. 공격적인 언행을 포함합니다.
- 나머지는 아젠다 기반으로 **최근 대화를 자연스럽게 이어받아** 업무 수행 방법을 논의합니다.
- 직전 발언을 참고해서 구체화하거나 보완하는 내용으로 작성합니다.
- 같은 문장이나 비슷한 표현을 반복하지 않습니다.
- 반드시 한국어 구어체로 자연스럽고 현실적인 톤으로 작성합니다.
- 번호 매기기나 목록형 문장 대신, 대화체로 1~2문장 정도로 간결하게 작성합니다.
- 괄호 (), [], 중괄호, <> 등 어떤 형태의 괄호도 사용하지 마세요.
- 스피커 이름이나 off_topic, agile_violation 여부를 문장에 표기하지 마세요.

출력 형식:
- 스피커 이름이나 따옴표 없이 한글 대화문 **한 문단**만 반환합니다.
- 예시: 그러면 이번 스프린트에 API 응답 캐싱부터 적용해보고, 로그 지표는 제가 정리할게요.
""",
            f"""You are an assistant generating meeting utterances.
Assign personas to participants and create dialogue that discusses how to execute work based on the meeting agenda.

Agenda:
{agenda}

Recent conversation:
{recent_text}

Personas:
{persona_lines}

Next speaker info:
- speaker: {planned_turn.speaker}
- off_topic: {planned_turn.is_off_topic}
- agile_violation: {planned_turn.is_agile_violation}

Rules:
- Generate **only one** utterance for {planned_turn.speaker}.
- If off_topic=true, include light chatter unrelated to the agenda.
- If agile_violation=true, include language where the speaker pushes their own viewpoint.
- Otherwise, follow the agenda and **naturally continue the recent conversation** about how to execute the work.
- Build on the immediate prior statement with specific details.
- Avoid repeating the same sentences or similar phrasing.
- Write in natural, realistic spoken English.
- Keep it concise: 1–2 sentences in conversational tone (no lists).
- Do not use any brackets: (), [], {}, <>.
- Do not mention the speaker name or flags in the utterance.

Output format:
- Return a single paragraph of plain English dialogue with no speaker name or quotes.
- Example: Then let's start by adding API response caching this sprint, and I'll draft the logging metrics.
""",
        )

    def _generate_utterance_text(
        self,
        prompt: str,
        stream: bool = False,
        print_stream: bool = False,
        stream_callback: Optional[Callable[[str, str], None]] = None,
        speaker: Optional[str] = None,
    ) -> str:
        """LLM에 대화 생성만 요청하고 텍스트를 반환한다."""
        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=stream,
        )

        if stream:
            return self._collect_stream_text(
                response,
                print_to_terminal=print_stream,
                stream_callback=stream_callback,
                speaker=speaker,
            )

        return (response.choices[0].message.content or "").strip()

    def _collect_stream_text(
        self,
        stream,
        print_to_terminal: bool = False,
        stream_callback: Optional[Callable[[str, str], None]] = None,
        speaker: Optional[str] = None,
    ) -> str:
        """스트리밍 응답에서 텍스트만 추출한다."""
        chunks: list[str] = []
        for event in stream:
            delta = None
            if event.choices:
                delta = getattr(event.choices[0], "delta", None)
            if not delta:
                continue
            content = getattr(delta, "content", None)

            if isinstance(content, str):
                chunks.append(content)
                if print_to_terminal:
                    print(content, end="", flush=True)
                if stream_callback and content:
                    stream_callback(speaker or "", content)
            elif isinstance(content, list):
                for part in content:
                    text = None
                    if hasattr(part, "text"):
                        text = getattr(part, "text", None)
                    elif isinstance(part, dict):
                        text = part.get("text")
                    if text:
                        chunks.append(text)
                        if print_to_terminal:
                            print(text, end="", flush=True)
                        if stream_callback:
                            stream_callback(speaker or "", text)

        if print_to_terminal:
            print()

        return "".join(chunks).strip()

    @staticmethod
    def _strip_speaker_prefix(text: str) -> str:
        """Remove accidental 'Name:' prefixes from the model output."""
        stripped = text.lstrip()
        for sep in (":", "：", "-", " -"):
            if sep in stripped:
                name, rest = stripped.split(sep, 1)
                # Heuristic: very short name (<=5 chars) followed by text
                if len(name.strip()) <= 5 and rest.strip():
                    return rest.strip()
        return stripped

    @staticmethod
    def _remove_brackets(text: str) -> str:
        """괄호류 문자를 모두 제거해 구어체에 남지 않도록 한다."""
        brackets = "()[]{}<>（）［］｛｝＜＞【】"
        cleaned = "".join(ch for ch in text if ch not in brackets)
        # collapse double spaces caused by removals
        return " ".join(cleaned.split())
