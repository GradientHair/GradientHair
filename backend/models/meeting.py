from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MeetingStatus(Enum):
    PREPARING = "preparing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class InterventionType(Enum):
    TOPIC_DRIFT = "TOPIC_DRIFT"
    PRINCIPLE_VIOLATION = "PRINCIPLE_VIOLATION"
    PARTICIPATION_IMBALANCE = "PARTICIPATION_IMBALANCE"
    DECISION_STYLE = "DECISION_STYLE"


@dataclass
class Participant:
    id: str
    name: str
    role: str
    speaking_time: float = 0.0
    speaking_count: int = 0


@dataclass
class TranscriptEntry:
    id: str
    timestamp: str
    speaker: str
    text: str
    duration: float = 0.0
    confidence: float = 1.0
    latency_ms: float | None = None


@dataclass
class Intervention:
    id: str
    timestamp: str
    intervention_type: InterventionType
    message: str
    trigger_context: str = ""
    violated_principle: Optional[str] = None
    parking_lot_item: Optional[str] = None
    suggested_speaker: Optional[str] = None


@dataclass
class MeetingState:
    meeting_id: str
    title: str
    status: MeetingStatus = MeetingStatus.PREPARING

    agenda: str = ""
    principles: list[dict] = field(default_factory=list)
    participants: list[Participant] = field(default_factory=list)

    transcript: list[TranscriptEntry] = field(default_factory=list)
    interventions: list[Intervention] = field(default_factory=list)
    parking_lot: list[str] = field(default_factory=list)

    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
