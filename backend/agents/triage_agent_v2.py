"""
TriageAgent: Decides which JudgeAgents to call based on current context and transcript.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.meeting_context import MeetingContext
    from models.meeting import TranscriptEntry

logger = logging.getLogger(__name__)


class TriageAgentV2:
    """
    Triage agent that decides which judge agents to invoke.

    Decision rules:
    - topic: Always check for topic drift (every N entries or keywords detected)
    - principle: Check when decision-making keywords detected
    - participation: Check periodically for balance
    """

    def __init__(self):
        self.topic_check_interval = 3  # Check topic every N entries
        self.participation_check_interval = 5
        self._entry_count = 0

        # Keywords that suggest potential issues
        self.off_topic_keywords = [
            "야구", "축구", "드라마", "영화", "주말", "날씨",
            "점심", "저녁", "커피", "게임", "여행"
        ]
        self.decision_keywords = [
            "결정", "정하자", "그렇게 하자", "내가 할게", "제가 하겠습니다",
            "그냥", "일단", "나중에", "빨리"
        ]

    async def decide(
        self,
        context: "MeetingContext",
        recent_transcript: list["TranscriptEntry"],
    ) -> list[str]:
        """
        Decide which judge agents to call.

        Returns:
            List of judge names to call: ["topic", "principle", "participation"]
        """
        self._entry_count += 1
        judges_to_call = []

        if not recent_transcript:
            return judges_to_call

        latest_entry = recent_transcript[-1]
        latest_text = latest_entry.text.lower() if latest_entry.text else ""

        # Topic check: periodic + keyword detection
        should_check_topic = (
            self._entry_count % self.topic_check_interval == 0
            or any(kw in latest_text for kw in self.off_topic_keywords)
        )
        if should_check_topic:
            judges_to_call.append("topic")
            logger.debug(f"[Triage] Will check topic (count={self._entry_count})")

        # Principle check: keyword detection
        if any(kw in latest_text for kw in self.decision_keywords):
            judges_to_call.append("principle")
            logger.debug(f"[Triage] Will check principle (keywords detected)")

        # Participation check: periodic
        if self._entry_count % self.participation_check_interval == 0:
            judges_to_call.append("participation")
            logger.debug(f"[Triage] Will check participation (count={self._entry_count})")

        # If context already has unresolved issues, re-check relevant judges
        if context.topic_analysis.status.value == "off_topic":
            if "topic" not in judges_to_call:
                judges_to_call.append("topic")

        if context.participation_analysis.is_imbalanced:
            if "participation" not in judges_to_call:
                judges_to_call.append("participation")

        if judges_to_call:
            logger.info(f"[TriageAgent] *** DECISION ***")
            logger.info(f"[TriageAgent]   entry #{self._entry_count}: {latest_text[:40]}...")
            logger.info(f"[TriageAgent]   judges_to_call: {judges_to_call}")
        return judges_to_call
