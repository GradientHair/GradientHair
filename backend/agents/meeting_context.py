"""
MeetingContext: Shared state for agent orchestration.

Flow:
1. Transcript added → TriageAgent decides which judges to call
2. JudgeAgents analyze and modify context
3. InterventionAgent observes context and decides to intervene
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Awaitable

from models.meeting import MeetingState, TranscriptEntry, Intervention, InterventionType


class TopicStatus(Enum):
    ON_TOPIC = "on_topic"
    DRIFTING = "drifting"
    OFF_TOPIC = "off_topic"


@dataclass
class TopicAnalysis:
    """Topic analysis result."""
    status: TopicStatus = TopicStatus.ON_TOPIC
    current_topic: str = ""
    drift_reason: str = ""
    confidence: float = 0.0
    parking_lot_suggestion: str = ""


@dataclass
class PrincipleViolation:
    """A detected principle violation."""
    principle_id: str
    principle_name: str
    violation_reason: str
    speaker: str
    timestamp: str
    severity: float = 0.5  # 0.0 ~ 1.0


@dataclass
class ParticipationAnalysis:
    """Participation balance analysis."""
    is_imbalanced: bool = False
    dominant_speaker: str = ""
    silent_participants: list[str] = field(default_factory=list)
    dominance_ratio: float = 0.0


@dataclass
class MeetingContext:
    """
    Shared context for all agents.
    JudgeAgents modify this context, InterventionAgent observes it.
    """
    meeting_state: MeetingState

    # Analysis results (modified by JudgeAgents)
    topic_analysis: TopicAnalysis = field(default_factory=TopicAnalysis)
    principle_violations: list[PrincipleViolation] = field(default_factory=list)
    participation_analysis: ParticipationAnalysis = field(default_factory=ParticipationAnalysis)

    # Pending issues for intervention (accumulated by JudgeAgents)
    pending_issues: list[str] = field(default_factory=list)

    # Rate limiting
    last_intervention_time: Optional[datetime] = None
    intervention_cooldown_seconds: float = 15.0

    # Recent transcript for analysis
    recent_transcript_count: int = 10

    def get_recent_transcript(self) -> list[TranscriptEntry]:
        """Get recent transcript entries for analysis."""
        return self.meeting_state.transcript[-self.recent_transcript_count:]

    def add_issue(self, issue: str) -> None:
        """Add a pending issue that may require intervention."""
        import logging
        logger = logging.getLogger(__name__)
        if issue not in self.pending_issues:
            self.pending_issues.append(issue)
            logger.info(f"[MeetingContext] Issue added: {issue}")

    def clear_issues(self) -> None:
        """Clear pending issues after intervention."""
        self.pending_issues.clear()

    def can_intervene(self) -> bool:
        """Check if enough time has passed since last intervention."""
        if self.last_intervention_time is None:
            return True
        elapsed = (datetime.utcnow() - self.last_intervention_time).total_seconds()
        return elapsed >= self.intervention_cooldown_seconds

    def mark_intervention(self) -> None:
        """Mark that an intervention was just made."""
        self.last_intervention_time = datetime.utcnow()
        self.clear_issues()


class AgentOrchestrator:
    """
    Orchestrates the agent flow:
    1. TriageAgent → decides which judges to call
    2. JudgeAgents → analyze and modify context
    3. InterventionAgent → observes and sends WebSocket
    """

    def __init__(
        self,
        send_intervention: Callable[[Intervention], Awaitable[None]],
    ):
        self.send_intervention = send_intervention

        # Lazy import to avoid circular dependency
        from agents.triage_agent_v2 import TriageAgentV2
        from agents.topic_judge import TopicJudge
        from agents.principle_judge import PrincipleJudge
        from agents.participation_judge import ParticipationJudge
        from agents.intervention_agent import InterventionAgentV2

        self.triage_agent = TriageAgentV2()
        self.judges = {
            "topic": TopicJudge(),
            "principle": PrincipleJudge(),
            "participation": ParticipationJudge(),
        }
        self.intervention_agent = InterventionAgentV2()

    async def process_transcript(self, context: MeetingContext) -> Optional[Intervention]:
        """
        Process new transcript entry through the agent pipeline.
        Returns Intervention if one was sent, None otherwise.
        """
        import logging
        logger = logging.getLogger(__name__)

        recent = context.get_recent_transcript()
        if not recent:
            return None

        latest = recent[-1]
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"[AgentOrchestrator] *** PIPELINE START ***")
        logger.info(f"[AgentOrchestrator] New transcript: {latest.speaker}: {latest.text[:50]}...")
        logger.info(f"{'='*60}")

        # 1. Triage: decide which judges to call
        logger.info(f"[AgentOrchestrator] Step 1: TriageAgent deciding...")
        judges_to_call = await self.triage_agent.decide(context, recent)

        # 2. Run judges in parallel (they modify context)
        if judges_to_call:
            logger.info(f"[AgentOrchestrator] Step 2: Running JudgeAgents: {judges_to_call}")
            tasks = []
            for judge_name in judges_to_call:
                if judge_name in self.judges:
                    tasks.append(self.judges[judge_name].analyze(context, recent))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"[AgentOrchestrator] Step 2: JudgeAgents completed")
        else:
            logger.info(f"[AgentOrchestrator] Step 2: No judges to call")

        # 3. Intervention agent observes context and decides to intervene
        logger.info(f"[AgentOrchestrator] Step 3: InterventionAgent checking context...")
        intervention = await self.intervention_agent.check_and_intervene(context)

        if intervention:
            # Send via WebSocket
            logger.info(f"[AgentOrchestrator] *** INTERVENTION TRIGGERED ***")
            logger.info(f"[AgentOrchestrator]   type: {intervention.intervention_type.value}")
            logger.info(f"[AgentOrchestrator]   message: {intervention.message}")
            logger.info(f"[AgentOrchestrator] Sending via WebSocket...")
            await self.send_intervention(intervention)
            context.mark_intervention()
            logger.info(f"[AgentOrchestrator] *** PIPELINE END (with intervention) ***")
            return intervention

        logger.info(f"[AgentOrchestrator] *** PIPELINE END (no intervention) ***")
        return None
