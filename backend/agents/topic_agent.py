"""Topic Agent - 주제 이탈 감지"""
import os
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from agents.base_agent import BaseAgent, AnalysisResult
from models.meeting import MeetingState, TranscriptEntry


class TopicDriftResponse(BaseModel):
    is_off_topic: bool = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    off_topic_content: Optional[str] = None
    parking_lot_item: Optional[str] = None


class TopicAgent(BaseAgent):
    """주제 이탈을 감지하고 Parking Lot 처리하는 Agent"""

    def __init__(self):
        super().__init__("TopicAgent")
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.max_retries = 2

    async def analyze(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry]
    ) -> AnalysisResult:
        if len(recent_transcript) < 1:
            return AnalysisResult(agent_name=self.name, needs_intervention=False)

        transcript_text = "\n".join(
            [f"{t.speaker}: {t.text}" for t in recent_transcript[-5:]]
        )

        prompt = f"""당신은 회의 주제 이탈을 감지하는 전문가입니다.

아젠다:
{state.agenda or "아젠다 없음"}

최근 대화:
{transcript_text}

주제 이탈 여부를 판단하세요. 회의와 관련 없는 잡담(점심 메뉴, 날씨 등)은 주제 이탈입니다.

JSON 응답:
{{
  "is_off_topic": true/false,
  "confidence": 0.0-1.0,
  "off_topic_content": "이탈한 주제 (이탈 시)",
  "parking_lot_item": "Parking Lot에 추가할 항목 (이탈 시)"
}}
"""

        if self.client is None:
            return AnalysisResult(agent_name=self.name, needs_intervention=False)

        response_text = self._call_model_with_retry(prompt)
        if response_text is None:
            return AnalysisResult(agent_name=self.name, needs_intervention=False)

        try:
            parsed = TopicDriftResponse.model_validate_json(response_text)
        except ValidationError:
            return AnalysisResult(agent_name=self.name, needs_intervention=False)

        if parsed.is_off_topic and parsed.confidence > 0.7:
            parking_lot = parsed.parking_lot_item
            return AnalysisResult(
                agent_name=self.name,
                needs_intervention=True,
                intervention_type="TOPIC_DRIFT",
                message=f"잠깐요, 아젠다에서 벗어났어요. 원래 주제로 돌아갈게요.{f' {parking_lot}은(는) Parking Lot에 추가했습니다.' if parking_lot else ''}",
                confidence=parsed.confidence,
                parking_lot_item=parking_lot,
            )

        return AnalysisResult(agent_name=self.name, needs_intervention=False)

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
