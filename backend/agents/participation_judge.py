"""
ParticipationJudge: Analyzes participation balance and modifies context.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.meeting_context import MeetingContext
    from models.meeting import TranscriptEntry

logger = logging.getLogger(__name__)


class ParticipationJudge:
    """
    Judge agent that analyzes participation balance.
    Modifies context.participation_analysis based on analysis.
    """

    def __init__(self):
        self.imbalance_threshold = 0.5  # One speaker > 50% is imbalanced
        self.min_entries_for_analysis = 5

    async def analyze(
        self,
        context: "MeetingContext",
        recent_transcript: list["TranscriptEntry"],
    ) -> None:
        """
        Analyze participation balance and update context.
        """
        from agents.meeting_context import ParticipationAnalysis

        participants = context.meeting_state.participants
        if not participants or len(recent_transcript) < self.min_entries_for_analysis:
            return

        # Count speaking instances per participant
        speaker_counts: dict[str, int] = {}
        for entry in recent_transcript:
            speaker = entry.speaker
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

        total_utterances = sum(speaker_counts.values())
        if total_utterances == 0:
            return

        # Find dominant speaker
        dominant_speaker = max(speaker_counts, key=speaker_counts.get)
        dominance_ratio = speaker_counts[dominant_speaker] / total_utterances

        # Find silent participants
        participant_names = {p.name for p in participants}
        speakers_in_transcript = set(speaker_counts.keys())
        silent_participants = list(participant_names - speakers_in_transcript)

        # Also check participants with very low participation
        for p in participants:
            if p.name in speaker_counts:
                ratio = speaker_counts[p.name] / total_utterances
                if ratio < 0.1 and p.name not in silent_participants:  # Less than 10%
                    silent_participants.append(p.name)

        # Determine if imbalanced
        is_imbalanced = (
            dominance_ratio > self.imbalance_threshold
            or len(silent_participants) > 0
        )

        old_imbalanced = context.participation_analysis.is_imbalanced
        context.participation_analysis = ParticipationAnalysis(
            is_imbalanced=is_imbalanced,
            dominant_speaker=dominant_speaker if dominance_ratio > self.imbalance_threshold else "",
            silent_participants=silent_participants,
            dominance_ratio=dominance_ratio,
        )

        if is_imbalanced:
            logger.info(f"[ParticipationJudge] *** CONTEXT CHANGED ***")
            logger.info(f"[ParticipationJudge]   is_imbalanced: {old_imbalanced} → {is_imbalanced}")
            if silent_participants:
                context.add_issue(
                    f"참여 불균형: {', '.join(silent_participants)}님의 의견도 들어보면 좋겠습니다"
                )
                logger.info(f"[ParticipationJudge]   silent_participants: {silent_participants}")
            elif dominance_ratio > self.imbalance_threshold:
                context.add_issue(
                    f"참여 불균형: {dominant_speaker}님이 대화의 {dominance_ratio*100:.0f}%를 차지하고 있습니다"
                )
                logger.info(f"[ParticipationJudge]   dominant: {dominant_speaker} ({dominance_ratio*100:.0f}%)")
