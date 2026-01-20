"""Principle Agent - 회의 원칙 위반 감지"""
import json
from openai import OpenAI
from agents.base_agent import BaseAgent, AnalysisResult
from models.meeting import MeetingState, TranscriptEntry


class PrincipleAgent(BaseAgent):
    """회의 원칙 위반을 감지하는 Agent"""

    def __init__(self):
        super().__init__("PrincipleAgent")
        self.client = OpenAI()

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

        principles_text = "\n".join(
            [f"- {p.get('name', '')}" for p in state.principles]
        )

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

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        if result.get("is_violation") and result.get("confidence", 0) > 0.7:
            violated = result.get("violated_principle", "회의 원칙")
            return AnalysisResult(
                agent_name=self.name,
                needs_intervention=True,
                intervention_type="PRINCIPLE_VIOLATION",
                message=f"멈춰주세요! '{violated}' 원칙 위반입니다. 다른 분들 의견은 어떠세요?",
                confidence=result.get("confidence", 0.8),
                violated_principle=violated,
            )

        return AnalysisResult(agent_name=self.name, needs_intervention=False)
