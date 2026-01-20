"""Principle Agent - 회의 원칙 위반 감지"""
import os
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from agents.base_agent import BaseAgent, AnalysisResult
from models.meeting import MeetingState, TranscriptEntry
from services.principles_service import PrinciplesService


class PrincipleViolationResponse(BaseModel):
    is_violation: bool = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    violated_principle: Optional[str] = None
    violation_reason: Optional[str] = None



class PrincipleAgent(BaseAgent):
    """회의 원칙 위반을 감지하는 Agent"""

    def __init__(self):
        super().__init__("PrincipleAgent")
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.principles_service = PrinciplesService()
        self.max_retries = 2

    async def analyze(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry]
    ) -> AnalysisResult:
        if len(recent_transcript) < 1 or not state.principles:
            return AnalysisResult(agent_name=self.name, needs_intervention=False)

        transcript_text = "\n".join(
            [f"{t.speaker}: {t.text}" for t in recent_transcript[-5:]]
        )

        principles_text = "\n".join(self._build_principles_text(state))

        prompt = f"""당신은 회의 원칙 준수를 감시하는 전문가입니다.

회의 원칙:
{principles_text}

최근 대화:
{transcript_text}

원칙 위반 여부를 판단하세요.
주요 위반 사례:
- "수평적 의사결정" 위반: 혼자서 결정하거나 다른 의견을 묻지 않음
- "타임박스" 위반: 시간 관리 무시
- "Disagree and Commit" 위반: 반대 의견 없이 무조건 수용

JSON 응답:
{{
  "is_violation": true/false,
  "confidence": 0.0-1.0,
  "violated_principle": "위반된 원칙명 (위반 시)",
  "violation_reason": "위반 이유 (위반 시)"
}}
"""

        if self.client is None:
            return self._fallback_analysis(state, recent_transcript)

        response_text = self._call_model_with_retry(prompt)
        if response_text is None:
            return self._fallback_analysis(state, recent_transcript)

        try:
            parsed = PrincipleViolationResponse.model_validate_json(response_text)
        except ValidationError:
            return self._fallback_analysis(state, recent_transcript)

        if parsed.is_violation and parsed.confidence > 0.7:
            violated = parsed.violated_principle or "회의 원칙"
            return AnalysisResult(
                agent_name=self.name,
                needs_intervention=True,
                intervention_type="PRINCIPLE_VIOLATION",
                message=f"멈춰주세요! '{violated}' 원칙 위반입니다. 다른 분들 의견은 어떠세요?",
                confidence=parsed.confidence,
                violated_principle=violated,
            )

        return AnalysisResult(agent_name=self.name, needs_intervention=False)

    def _build_principles_text(self, state: MeetingState) -> list[str]:
        lines: list[str] = []
        for principle in state.principles:
            p_id = principle.get("id", "")
            p_name = principle.get("name", "")
            detail = self.principles_service.get_principle(p_id) if p_id else None
            if detail:
                summary = self._summarize_principle(detail.content)
                lines.append(f"- {detail.name}: {summary}")
            else:
                lines.append(f"- {p_name}")
        return lines

    def _call_model_with_retry(self, prompt: str) -> Optional[str]:
        last_error = None
        for attempt in range(self.max_retries + 1):
            messages = [{"role": "user", "content": prompt}]
            if last_error is not None:
                messages.append({
                    "role": "user",
                    "content": f"이전 응답 처리 중 오류가 발생했습니다: {last_error}. 올바른 JSON만 다시 출력하세요.",
                })
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content
            except Exception as exc:  # noqa: BLE001 - surface error to retry
                last_error = str(exc)
                continue
        return None

    def _fallback_analysis(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry],
    ) -> AnalysisResult:
        # Heuristic: if meeting has repeated unilateral decision phrases
        recent_text = " ".join(t.text for t in recent_transcript[-3:])
        keywords = ["결정", "그냥", "바로 하자", "내가 할게", "따라"]
        if any(k in recent_text for k in keywords):
            return AnalysisResult(
                agent_name=self.name,
                needs_intervention=True,
                intervention_type="PRINCIPLE_VIOLATION",
                message="멈춰주세요! 원칙 위반 가능성이 있어요. 다른 분들 의견을 들어보죠.",
                confidence=0.6,
                violated_principle="회의 원칙",
            )
        return AnalysisResult(agent_name=self.name, needs_intervention=False)

    def _summarize_principle(self, content: str) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        bullets = [line for line in lines if line[0].isdigit() or line.startswith("-")]
        summary = ", ".join(bullets[:3]) if bullets else (lines[1] if len(lines) > 1 else lines[0])
        return summary[:200]
