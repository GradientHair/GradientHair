"""
TopicJudge: Analyzes transcript for topic drift and modifies context.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from openai import OpenAI

from services.model_router import ModelRouter

if TYPE_CHECKING:
    from agents.meeting_context import MeetingContext, TopicStatus
    from models.meeting import TranscriptEntry

logger = logging.getLogger(__name__)


class TopicJudge:
    """
    Judge agent that analyzes topic drift.
    Modifies context.topic_analysis based on analysis.
    """

    def __init__(self):
        self.client = OpenAI()
        self.model = ModelRouter.select("fast", structured_output=True, api="chat")

        # Keywords for quick heuristic check
        self.off_topic_keywords = [
            "야구", "축구", "드라마", "영화", "주말", "날씨",
            "점심", "저녁", "커피", "게임", "여행", "휴가"
        ]

    async def analyze(
        self,
        context: "MeetingContext",
        recent_transcript: list["TranscriptEntry"],
    ) -> None:
        """
        Analyze transcript for topic drift and update context.
        """
        from agents.meeting_context import TopicStatus, TopicAnalysis

        if not recent_transcript:
            return

        agenda = context.meeting_state.agenda or "일반 회의"
        latest_text = recent_transcript[-1].text if recent_transcript else ""

        # Quick heuristic check first
        off_topic_detected = any(
            kw in latest_text for kw in self.off_topic_keywords
        )

        if off_topic_detected:
            # Detected off-topic via heuristic
            old_status = context.topic_analysis.status.value
            context.topic_analysis = TopicAnalysis(
                status=TopicStatus.OFF_TOPIC,
                current_topic=agenda,
                drift_reason=f"회의 주제와 관련 없는 내용 감지: {latest_text[:50]}",
                confidence=0.8,
                parking_lot_suggestion=f"'{latest_text[:30]}...' 관련 논의는 나중에",
            )
            context.add_issue(f"주제 이탈: {latest_text[:50]}")
            logger.info(f"[TopicJudge] *** CONTEXT CHANGED ***")
            logger.info(f"[TopicJudge]   topic_analysis.status: {old_status} → {context.topic_analysis.status.value}")
            logger.info(f"[TopicJudge]   drift_reason: {context.topic_analysis.drift_reason}")
            return

        # If not obviously off-topic, use LLM for deeper analysis
        try:
            result = await self._llm_analyze(agenda, recent_transcript)
            if result:
                context.topic_analysis = result
                if result.status == TopicStatus.OFF_TOPIC:
                    context.add_issue(f"주제 이탈: {result.drift_reason}")
                    logger.info(f"[TopicJudge] Off-topic detected (LLM): {result.drift_reason}")
                elif result.status == TopicStatus.DRIFTING:
                    logger.info(f"[TopicJudge] Topic drifting: {result.drift_reason}")
                else:
                    logger.debug("[TopicJudge] On topic")
        except Exception as e:
            logger.warning(f"[TopicJudge] LLM analysis failed: {e}")

    async def _llm_analyze(
        self,
        agenda: str,
        recent_transcript: list["TranscriptEntry"],
    ) -> "TopicAnalysis | None":
        """Use LLM for topic drift analysis."""
        from agents.meeting_context import TopicStatus, TopicAnalysis

        transcript_text = "\n".join(
            f"{e.speaker}: {e.text}" for e in recent_transcript[-5:]
        )

        prompt = f"""회의 아젠다: {agenda}

최근 대화:
{transcript_text}

위 대화가 회의 아젠다와 관련이 있는지 분석하세요.
JSON 형식으로 응답하세요:
{{
    "status": "on_topic" | "drifting" | "off_topic",
    "reason": "판단 이유",
    "confidence": 0.0~1.0
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=200,
            )

            import json
            content = response.choices[0].message.content
            data = json.loads(content)

            status_map = {
                "on_topic": TopicStatus.ON_TOPIC,
                "drifting": TopicStatus.DRIFTING,
                "off_topic": TopicStatus.OFF_TOPIC,
            }

            return TopicAnalysis(
                status=status_map.get(data.get("status"), TopicStatus.ON_TOPIC),
                current_topic=agenda,
                drift_reason=data.get("reason", ""),
                confidence=float(data.get("confidence", 0.5)),
            )
        except Exception as e:
            logger.error(f"[TopicJudge] LLM error: {e}")
            return None
