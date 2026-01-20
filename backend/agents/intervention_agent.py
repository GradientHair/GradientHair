"""
InterventionAgent: Observes context and decides when to intervene.
Sends interventions via WebSocket to frontend.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from agents.meeting_context import MeetingContext

from models.meeting import Intervention, InterventionType

logger = logging.getLogger(__name__)


class InterventionAgentV2:
    """
    Intervention agent that observes context and decides when to intervene.
    Creates Intervention objects to be sent via WebSocket.
    """

    def __init__(self):
        self.message_templates = {
            "topic_drift": [
                "회의 주제로 돌아가볼까요?",
                "아젠다에 집중해주세요.",
                "그 이야기는 파킹랏에 추가하고 본 주제로 돌아가시죠.",
            ],
            "principle_violation": [
                "모든 분의 의견을 들어보고 결정하면 어떨까요?",
                "좀 더 논의가 필요해 보입니다.",
                "다른 분들의 의견도 궁금합니다.",
            ],
            "participation_imbalance": [
                "{silent}님의 의견도 들어보면 좋겠습니다.",
                "아직 말씀 안 하신 분도 계시네요. {silent}님은 어떻게 생각하세요?",
                "다양한 관점을 듣고 싶습니다. {silent}님?",
            ],
        }

    async def check_and_intervene(
        self,
        context: "MeetingContext",
    ) -> Optional[Intervention]:
        """
        Check context and create intervention if needed.

        Returns:
            Intervention if intervention is needed, None otherwise.
        """
        from agents.meeting_context import TopicStatus

        logger.info(f"[InterventionAgent] *** OBSERVING CONTEXT ***")
        logger.info(f"[InterventionAgent]   topic_status: {context.topic_analysis.status.value}")
        logger.info(f"[InterventionAgent]   principle_violations: {len(context.principle_violations)}")
        logger.info(f"[InterventionAgent]   participation_imbalanced: {context.participation_analysis.is_imbalanced}")
        logger.info(f"[InterventionAgent]   pending_issues: {context.pending_issues}")

        # Check cooldown
        if not context.can_intervene():
            logger.info("[InterventionAgent]   → Cooldown active, skipping intervention")
            return None

        # No pending issues
        if not context.pending_issues:
            logger.info("[InterventionAgent]   → No pending issues, no intervention needed")
            return None

        # Prioritize interventions
        # 1. Topic drift (highest priority)
        if context.topic_analysis.status == TopicStatus.OFF_TOPIC:
            return self._create_topic_intervention(context)

        # 2. Principle violations
        if context.principle_violations:
            return self._create_principle_intervention(context)

        # 3. Participation imbalance
        if context.participation_analysis.is_imbalanced:
            return self._create_participation_intervention(context)

        # Generic intervention for other issues
        if context.pending_issues:
            return self._create_generic_intervention(context)

        return None

    def _create_topic_intervention(self, context: "MeetingContext") -> Intervention:
        """Create intervention for topic drift."""
        import random

        analysis = context.topic_analysis
        message = random.choice(self.message_templates["topic_drift"])

        intervention = Intervention(
            id=f"int_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow().isoformat(),
            intervention_type=InterventionType.TOPIC_DRIFT,
            message=message,
            trigger_context=analysis.drift_reason,
            parking_lot_item=analysis.parking_lot_suggestion or None,
        )

        logger.info(f"[InterventionAgent] Topic drift intervention: {message}")
        return intervention

    def _create_principle_intervention(self, context: "MeetingContext") -> Intervention:
        """Create intervention for principle violation."""
        import random

        # Get most recent violation
        violation = context.principle_violations[-1]
        message = random.choice(self.message_templates["principle_violation"])

        intervention = Intervention(
            id=f"int_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow().isoformat(),
            intervention_type=InterventionType.PRINCIPLE_VIOLATION,
            message=message,
            trigger_context=f"{violation.speaker}: {violation.violation_reason}",
            violated_principle=violation.principle_name,
        )

        logger.info(f"[InterventionAgent] Principle violation intervention: {message}")
        return intervention

    def _create_participation_intervention(self, context: "MeetingContext") -> Intervention:
        """Create intervention for participation imbalance."""
        import random

        analysis = context.participation_analysis

        if analysis.silent_participants:
            silent = analysis.silent_participants[0]
            template = random.choice(self.message_templates["participation_imbalance"])
            message = template.format(silent=silent)
            suggested_speaker = silent
        else:
            message = "다른 분들의 의견도 들어보면 좋겠습니다."
            suggested_speaker = None

        intervention = Intervention(
            id=f"int_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow().isoformat(),
            intervention_type=InterventionType.PARTICIPATION_IMBALANCE,
            message=message,
            trigger_context=f"dominant: {analysis.dominant_speaker} ({analysis.dominance_ratio*100:.0f}%)",
            suggested_speaker=suggested_speaker,
        )

        logger.info(f"[InterventionAgent] Participation intervention: {message}")
        return intervention

    def _create_generic_intervention(self, context: "MeetingContext") -> Intervention:
        """Create generic intervention for other issues."""
        issue = context.pending_issues[0] if context.pending_issues else "회의 진행 확인"

        intervention = Intervention(
            id=f"int_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow().isoformat(),
            intervention_type=InterventionType.TOPIC_DRIFT,  # Default type
            message="회의 진행에 주의가 필요합니다.",
            trigger_context=issue,
        )

        logger.info(f"[InterventionAgent] Generic intervention for: {issue}")
        return intervention
