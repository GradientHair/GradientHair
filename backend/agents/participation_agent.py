"""Participation Agent - 발언 균형 감지"""
from agents.base_agent import BaseAgent, AnalysisResult
from models.meeting import MeetingState, TranscriptEntry
from i18n import pick


class ParticipationAgent(BaseAgent):
    """발언 불균형을 감지하고 참여를 독려하는 Agent"""

    def __init__(self):
        super().__init__("ParticipationAgent")
        self.min_utterances_to_check = 5  # 최소 발화 수

    async def analyze(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry]
    ) -> AnalysisResult:
        if len(state.participants) < 2:
            return AnalysisResult(agent_name=self.name, needs_intervention=False)

        # 총 발언 수 계산
        total_count = sum(p.speaking_count for p in state.participants)
        if total_count < self.min_utterances_to_check:
            return AnalysisResult(agent_name=self.name, needs_intervention=False)

        # 발언하지 않은 참석자 찾기
        silent_participants = [
            p for p in state.participants if p.speaking_count == 0
        ]

        if silent_participants:
            silent = silent_participants[0]
            return AnalysisResult(
                agent_name=self.name,
                needs_intervention=True,
                intervention_type="PARTICIPATION_IMBALANCE",
                message=pick(
                    f"잠깐요! {silent.name} 님 아직 발언 안 하셨어요. {silent.role} 관점에서 어떻게 보세요?",
                    f"Quick check-in: {silent.name} hasn't spoken yet. How do you see it from a {silent.role} perspective?",
                ),
                confidence=0.9,
                suggested_speaker=silent.name,
            )

        # 발언 불균형 체크 (한 사람이 50% 이상 차지)
        for p in state.participants:
            percentage = (p.speaking_count / total_count) * 100 if total_count > 0 else 0
            if percentage > 50:
                # 가장 적게 발언한 사람 찾기
                least_speaker = min(state.participants, key=lambda x: x.speaking_count)
                if least_speaker.speaking_count < total_count * 0.1:  # 10% 미만
                    return AnalysisResult(
                        agent_name=self.name,
                        needs_intervention=True,
                        intervention_type="PARTICIPATION_IMBALANCE",
                        message=pick(
                            f"잠깐요! {p.name} 님이 대부분 발언하고 계세요. {least_speaker.name} 님 의견도 들어볼까요?",
                            f"Hold on—{p.name} is doing most of the talking. Can we hear from {least_speaker.name} too?",
                        ),
                        confidence=0.85,
                        suggested_speaker=least_speaker.name,
                    )

        return AnalysisResult(agent_name=self.name, needs_intervention=False)
