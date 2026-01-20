"""Base Agent class for all specialized agents."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from models.meeting import MeetingState, TranscriptEntry


@dataclass
class AnalysisResult:
    """분석 결과"""
    agent_name: str
    needs_intervention: bool
    intervention_type: Optional[str] = None
    message: Optional[str] = None
    confidence: float = 0.0
    violated_principle: Optional[str] = None
    parking_lot_item: Optional[str] = None
    suggested_speaker: Optional[str] = None


class BaseAgent(ABC):
    """모든 전문 Agent의 기본 클래스"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def analyze(
        self,
        state: MeetingState,
        recent_transcript: list[TranscriptEntry]
    ) -> AnalysisResult:
        """발화 분석 및 개입 필요 여부 판단"""
        pass
