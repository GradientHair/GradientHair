from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Participant(BaseModel):
    name: str
    role: str | None = None


class MeetingCreate(BaseModel):
    title: str
    agenda: str
    participants: list[Participant] = Field(default_factory=list)
    demo_script_id: str | None = None


class DemoStartRequest(BaseModel):
    demo_script_id: str | None = None


class MeetingRecord(BaseModel):
    id: str
    title: str
    agenda: str
    participants: list[Participant]
    status: Literal["preparing", "in_progress", "completed"] = "preparing"
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None


class DemoEvent(BaseModel):
    id: str
    type: Literal["system", "transcript", "intervention", "recap", "meeting_end"]
    delay_ms: int
    payload: dict


class DemoStartResponse(BaseModel):
    meeting: MeetingRecord
    events: list[DemoEvent]


class DemoScriptSummary(BaseModel):
    id: str
    title: str
    agenda: list[str]
    participants: list[Participant]
    description: str | None = None


class DemoScript(BaseModel):
    id: str
    title: str
    agenda: list[str]
    participants: list[Participant]
    steps: list[dict]
    action_items: list[dict] = Field(default_factory=list)
    description: str | None = None
