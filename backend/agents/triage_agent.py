"""Triage Agent - 발화 분석 및 전문 Agent로 Handoff"""
import asyncio
import time
import uuid
from datetime import datetime
from typing import Optional

from agents.base_agent import AnalysisResult
from agents.topic_agent import TopicAgent
from agents.principle_agent import PrincipleAgent
from agents.participation_agent import ParticipationAgent
from models.meeting import MeetingState, TranscriptEntry, Intervention, InterventionType


class TriageAgent:
    """발화를 분석하고 전문 Agent들에게 병렬로 Handoff하는 Agent"""

    def __init__(self):
        self.topic_agent = TopicAgent()
        self.principle_agent = PrincipleAgent()
        self.participation_agent = ParticipationAgent()

        self.last_intervention_time = 0
        self.min_intervention_interval = 15  # 최소 15초 간격

    async def analyze(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry]
    ) -> Optional[Intervention]:
        """병렬로 모든 Agent 분석 후 개입 결정"""

        # 최소 간격 체크
        current_time = time.time()
        if current_time - self.last_intervention_time < self.min_intervention_interval:
            return None

        if len(recent_transcript) < 2:
            return None

        # 병렬 분석 실행
        results = await asyncio.gather(
            self.topic_agent.analyze(state, recent_transcript),
            self.principle_agent.analyze(state, recent_transcript),
            self.participation_agent.analyze(state, recent_transcript),
            return_exceptions=True
        )

        # 결과 필터링 (에러 제외, 개입 필요한 것만)
        valid_results: list[AnalysisResult] = []
        for r in results:
            if isinstance(r, AnalysisResult) and r.needs_intervention:
                valid_results.append(r)

        if not valid_results:
            return None

        # 가장 신뢰도 높은 결과 선택 (또는 병합)
        intervention = self._merge_interventions(valid_results)
        if intervention:
            self.last_intervention_time = current_time

        return intervention

    def _merge_interventions(
        self,
        results: list[AnalysisResult]
    ) -> Optional[Intervention]:
        """여러 개입 결과를 하나로 병합"""
        if not results:
            return None

        # 우선순위: PRINCIPLE_VIOLATION > TOPIC_DRIFT > PARTICIPATION_IMBALANCE
        priority = {
            "PRINCIPLE_VIOLATION": 3,
            "TOPIC_DRIFT": 2,
            "PARTICIPATION_IMBALANCE": 1,
        }

        # 우선순위 + 신뢰도로 정렬
        sorted_results = sorted(
            results,
            key=lambda r: (priority.get(r.intervention_type, 0), r.confidence),
            reverse=True
        )

        best = sorted_results[0]

        return Intervention(
            id=f"int_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow().isoformat(),
            intervention_type=InterventionType(best.intervention_type),
            message=best.message,
            trigger_context=f"Detected by {best.agent_name}",
            violated_principle=best.violated_principle,
            parking_lot_item=best.parking_lot_item,
            suggested_speaker=best.suggested_speaker,
        )
