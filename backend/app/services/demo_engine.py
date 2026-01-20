from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import itertools
from typing import Any

import anyio

from app.models import DemoEvent, DemoScript, MeetingRecord
from app.services.openai_service import OpenAIService
from app.services.storage_service import StorageService
from app.services.text_utils import extract_candidate_names


@dataclass
class DemoTimeline:
    events: list[DemoEvent]
    recap: dict[str, Any]
    transcript: list[dict]
    interventions: list[dict]
    saved_files: list[str]


class DemoEngine:
    def __init__(self, meeting: MeetingRecord, script: DemoScript) -> None:
        self.meeting = meeting
        self.script = script
        self.events: list[DemoEvent] = []
        self.transcript: list[dict] = []
        self.interventions: list[dict] = []
        self.speaker_counts = {p.name: 0 for p in meeting.participants}
        self.speaker_spoken = set()
        self.attendance_checked = False
        self.imbalance_triggered = False
        self.openai = OpenAIService()
        self.storage = StorageService()
        self._event_counter = itertools.count(1)

    async def build(self) -> DemoTimeline:
        self._emit_ice_breaker()
        self.storage.save_preparation(
            self.meeting.id,
            self.meeting.title,
            self.meeting.agenda,
            [p.model_dump() for p in self.meeting.participants],
        )

        for step in self.script.steps:
            if step.get("type", "utterance") != "utterance":
                continue
            entry = self._record_transcript(step)
            self._maybe_fix_attendance(step, entry)
            self._maybe_flag_topics(step, entry)
            self._maybe_flag_principles(step, entry)
            self._maybe_flag_participation(step)

        recap = await self._generate_recap()
        self._emit_recap(recap)
        saved_files = self._save_files(recap)
        self._emit_meeting_end(saved_files)

        return DemoTimeline(
            events=self.events,
            recap=recap,
            transcript=self.transcript,
            interventions=self.interventions,
            saved_files=saved_files,
        )

    def _emit_ice_breaker(self) -> None:
        participants = ", ".join(
            [f"{p.name} ({p.role or 'Role'})" for p in self.meeting.participants]
        )
        message = (
            "Ice breaker: Here is the attendee list I have on file: "
            f"{participants}. Please confirm who's here." 
        )
        self._add_event(
            event_type="system",
            delay_ms=600,
            payload={
                "kind": "ICE_BREAKER",
                "message": message,
                "attendees": [p.model_dump() for p in self.meeting.participants],
            },
        )

    def _record_transcript(self, step: dict) -> dict:
        entry = {
            "id": f"tr_{next(self._event_counter)}",
            "speaker": step.get("speaker", "Unknown"),
            "text": step.get("text", ""),
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        }
        delay_ms = int(step.get("delay_ms", 1200))
        self._add_event("transcript", delay_ms, entry)
        self.transcript.append(entry)
        self.speaker_counts[entry["speaker"]] = self.speaker_counts.get(entry["speaker"], 0) + 1
        self.speaker_spoken.add(entry["speaker"])
        return entry

    def _maybe_fix_attendance(self, step: dict, entry: dict) -> None:
        mentions = step.get("mentions") or extract_candidate_names(entry["text"])
        if not mentions:
            return
        known = {p.name.lower(): p.name for p in self.meeting.participants}
        unknown = [name for name in mentions if name.lower() not in known]
        if not unknown:
            return
        message = (
            f"Correction: {', '.join(unknown)} is not on the attendee list. "
            "If someone new joined, add them. Otherwise we'll continue with the current list."
        )
        self._record_intervention(
            intervention_type="ATTENDEE_CORRECTION",
            message=message,
            metadata={"unknown_names": unknown},
            delay_ms=900,
        )

    def _maybe_flag_topics(self, step: dict, entry: dict) -> None:
        tags = step.get("tags", [])
        if "TOPIC_DRIFT" not in tags:
            return
        parking = step.get("parking_lot", "Off-topic item")
        message = (
            "Topic drift detected. Let's return to the agenda. "
            f"I parked '{parking}' for later."
        )
        self._record_intervention(
            intervention_type="TOPIC_DRIFT",
            message=message,
            metadata={"parkingLotItem": parking},
            delay_ms=1000,
        )

    def _maybe_flag_principles(self, step: dict, entry: dict) -> None:
        tags = step.get("tags", [])
        if "PRINCIPLE_VIOLATION" not in tags and "DECISION_STYLE" not in tags:
            return
        principle = step.get("principle", "Horizontal decision making")
        message = (
            "Pause. That sounds like a top-down decision. "
            f"We agreed on '{principle}'. Let's hear other voices first."
        )
        self._record_intervention(
            intervention_type="PRINCIPLE_VIOLATION",
            message=message,
            metadata={"principle": principle},
            delay_ms=1000,
        )

    def _maybe_flag_participation(self, step: dict) -> None:
        if self.imbalance_triggered:
            return
        if len(self.transcript) < 3:
            return
        silent = [p.name for p in self.meeting.participants if p.name not in self.speaker_spoken]
        if not silent:
            return
        target = silent[0]
        message = (
            f"Participation check: {target}, we haven't heard from you yet. "
            "What is your perspective on this agenda?"
        )
        self._record_intervention(
            intervention_type="PARTICIPATION_IMBALANCE",
            message=message,
            metadata={"target": target},
            delay_ms=1000,
        )
        self.imbalance_triggered = True

    def _record_intervention(self, intervention_type: str, message: str, metadata: dict, delay_ms: int) -> None:
        intervention = {
            "id": f"int_{next(self._event_counter)}",
            "type": intervention_type,
            "message": message,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
            "metadata": metadata,
            "playAlertSound": True,
        }
        self.interventions.append(intervention)
        self._add_event("intervention", delay_ms, intervention)

    async def _generate_recap(self) -> dict[str, Any]:
        payload = {
            "title": self.meeting.title,
            "agenda": self.meeting.agenda,
            "participants": [p.model_dump() for p in self.meeting.participants],
            "transcript": self.transcript,
            "interventions": self.interventions,
            "action_items": self.script.action_items,
        }
        recap = None
        if self.openai.is_available():
            recap = await anyio.to_thread.run_sync(self.openai.generate_recap, payload)
        if recap:
            recap["source"] = "openai"
            recap.setdefault("action_items", self.script.action_items)
            return recap

        summary = (
            "Discussed agenda items, confirmed attendees, and addressed off-topic drift. "
            f"Interventions: {len(self.interventions)}."
        )
        return {
            "summary": summary,
            "decisions": ["Finalize next sprint priorities"],
            "action_items": self.script.action_items,
            "risks": ["Unclear ownership for open issues"],
            "source": "fallback",
        }

    def _emit_recap(self, recap: dict[str, Any]) -> None:
        payload = {
            "summary": recap.get("summary", ""),
            "decisions": recap.get("decisions", []),
            "actionItems": recap.get("action_items", []),
            "risks": recap.get("risks", []),
            "source": recap.get("source"),
        }
        self._add_event("recap", 1200, payload)

    def _save_files(self, recap: dict[str, Any]) -> list[str]:
        files = []
        files.append(str(self.storage.save_transcript(self.meeting.id, self.meeting.title, self.transcript)))
        files.append(str(self.storage.save_interventions(self.meeting.id, self.meeting.title, self.interventions)))
        files.append(str(self.storage.save_summary(self.meeting.id, self.meeting.title, recap.get("summary", ""))))
        files.append(str(self.storage.save_action_items(
            self.meeting.id,
            self.meeting.title,
            recap.get("action_items", []),
        )))
        return files

    def _emit_meeting_end(self, saved_files: list[str]) -> None:
        self._add_event(
            "meeting_end",
            800,
            {
                "savedFiles": saved_files,
                "meetingId": self.meeting.id,
            },
        )

    def _add_event(self, event_type: str, delay_ms: int, payload: dict) -> None:
        event = DemoEvent(
            id=f"evt_{next(self._event_counter)}",
            type=event_type,
            delay_ms=delay_ms,
            payload=payload,
        )
        self.events.append(event)
