import json
import time
import uuid
from datetime import datetime
from openai import OpenAI
from models.meeting import (
    MeetingState,
    TranscriptEntry,
    Intervention,
    InterventionType,
)


class ModeratorAgent:
    def __init__(self):
        self.client = OpenAI()
        self.last_intervention_time = 0
        self.min_intervention_interval = 20  # 최소 20초 간격

    async def analyze(
        self, state: MeetingState, recent_transcript: list[TranscriptEntry]
    ) -> Intervention | None:
        # 최소 간격 체크
        current_time = time.time()
        if current_time - self.last_intervention_time < self.min_intervention_interval:
            return None

        if len(recent_transcript) < 2:
            return None

        # 발언 통계 계산
        speaker_stats = self._calculate_speaker_stats(state)

        # GPT-4o로 분석
        system_prompt = f"""당신은 회의 모더레이터 AI입니다.
아젠다: {state.agenda}
회의 원칙: {json.dumps([p.get('name', '') for p in state.principles], ensure_ascii=False)}
참석자: {json.dumps([p.name for p in state.participants], ensure_ascii=False)}
발언 통계: {json.dumps(speaker_stats, ensure_ascii=False)}

최근 대화를 분석하고 개입이 필요한지 판단하세요.
직접적이고 용기있게 개입하세요.

개입 유형:
- TOPIC_DRIFT: 주제 이탈 (예: "잠깐요, 아젠다에서 벗어났어요.")
- PRINCIPLE_VIOLATION: 원칙 위반 (예: "멈춰주세요! 원칙 위반입니다.")
- PARTICIPATION_IMBALANCE: 발언 불균형 (예: "잠깐요! OO님 아직 발언 안 하셨어요.")
- DECISION_STYLE: Top-down 결정 (예: "멈춰주세요! 혼자 결정하시면 안 돼요.")

JSON 응답:
{{
  "needs_intervention": true/false,
  "intervention_type": "TOPIC_DRIFT" | "PRINCIPLE_VIOLATION" | "PARTICIPATION_IMBALANCE" | "DECISION_STYLE" | null,
  "message": "개입 메시지 (한국어, 직접적인 톤)",
  "violated_principle": "위반 원칙명" | null,
  "parking_lot_item": "Parking Lot 항목" | null,
  "suggested_speaker": "발언 권유할 참석자" | null
}}
"""

        transcript_text = "\n".join(
            [f"{t.speaker}: {t.text}" for t in recent_transcript[-10:]]
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"최근 대화:\n{transcript_text}"},
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        if result.get("needs_intervention"):
            self.last_intervention_time = current_time
            return Intervention(
                id=f"int_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.utcnow().isoformat(),
                intervention_type=InterventionType(result["intervention_type"]),
                message=result["message"],
                trigger_context=recent_transcript[-1].text if recent_transcript else "",
                violated_principle=result.get("violated_principle"),
                parking_lot_item=result.get("parking_lot_item"),
                suggested_speaker=result.get("suggested_speaker"),
            )

        return None

    def _calculate_speaker_stats(self, state: MeetingState) -> dict:
        total_count = sum(p.speaking_count for p in state.participants)
        if total_count == 0:
            return {}

        return {
            p.name: {
                "percentage": round(p.speaking_count / total_count * 100),
                "count": p.speaking_count,
            }
            for p in state.participants
        }
