"""Topic Agent - 주제 이탈 감지"""
import asyncio
import os
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent, AnalysisResult
from models.meeting import MeetingState, TranscriptEntry
from services.llm_validation import LLMStructuredOutputRunner, ValidationResult
from services.model_router import ModelRouter
from i18n import pick


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
        self.runner = None
        if self.client:
            choice = ModelRouter.select("fast", structured_output=True, api="chat")
            self.runner = LLMStructuredOutputRunner(
                client=self.client,
                model=choice.model,
                schema=TopicDriftResponse,
                max_retries=self.max_retries,
                custom_validator=self._validate_response,
            )

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

        prompt = pick(
            f"""당신은 회의 주제 이탈을 감지하는 전문가입니다.

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
""",
            f"""You are an expert at detecting topic drift in meetings.

Agenda:
{state.agenda or "No agenda"}

Recent conversation:
{transcript_text}

Decide whether the discussion is off-topic. Casual chatter unrelated to the meeting (lunch, weather, etc.) is off-topic.

Respond as JSON:
{{
  "is_off_topic": true/false,
  "confidence": 0.0-1.0,
  "off_topic_content": "off-topic subject (if off-topic)",
  "parking_lot_item": "item to add to the parking lot (if off-topic)"
}}
""",
        )

        if self.runner is None:
            return AnalysisResult(agent_name=self.name, needs_intervention=False)
        parsed = await asyncio.to_thread(self.runner.run, prompt)
        if parsed is None:
            return AnalysisResult(agent_name=self.name, needs_intervention=False)

        if parsed.is_off_topic and parsed.confidence > 0.7:
            parking_lot = parsed.parking_lot_item
            parking_note_ko = f" {parking_lot}은(는) Parking Lot에 추가했습니다." if parking_lot else ""
            parking_note_en = f" I added {parking_lot} to the parking lot." if parking_lot else ""
            return AnalysisResult(
                agent_name=self.name,
                needs_intervention=True,
                intervention_type="TOPIC_DRIFT",
                message=pick(
                    f"잠깐요, 아젠다에서 벗어났어요. 원래 주제로 돌아갈게요.{parking_note_ko}",
                    f"Hold on, we're off the agenda. Let's return to the main topic.{parking_note_en}",
                ),
                confidence=parsed.confidence,
                parking_lot_item=parking_lot,
            )

        return AnalysisResult(agent_name=self.name, needs_intervention=False)

    def _validate_response(self, parsed: TopicDriftResponse) -> ValidationResult:
        if parsed.is_off_topic and not (parsed.parking_lot_item or parsed.off_topic_content):
            return ValidationResult(ok=False, error="off_topic_content or parking_lot_item required")
        return ValidationResult(ok=True, value=parsed)
