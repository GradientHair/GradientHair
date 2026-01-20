"""Topic Agent - 주제 이탈 감지"""
import json
from openai import OpenAI
from agents.base_agent import BaseAgent, AnalysisResult
from models.meeting import MeetingState, TranscriptEntry


class TopicAgent(BaseAgent):
    """주제 이탈을 감지하고 Parking Lot 처리하는 Agent"""

    def __init__(self):
        super().__init__("TopicAgent")
        self.client = OpenAI()

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

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        if result.get("is_off_topic") and result.get("confidence", 0) > 0.7:
            parking_lot = result.get("parking_lot_item")
            return AnalysisResult(
                agent_name=self.name,
                needs_intervention=True,
                intervention_type="TOPIC_DRIFT",
                message=f"잠깐요, 아젠다에서 벗어났어요. 원래 주제로 돌아갈게요.{f' {parking_lot}은(는) Parking Lot에 추가했습니다.' if parking_lot else ''}",
                confidence=result.get("confidence", 0.8),
                parking_lot_item=parking_lot,
            )

        return AnalysisResult(agent_name=self.name, needs_intervention=False)
