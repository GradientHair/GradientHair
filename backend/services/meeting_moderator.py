from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from models.meeting import MeetingState, TranscriptEntry
from services.storage_service import StorageService


class MeetingModerator:
    """Context manager that syncs MeetingState from transcript log."""

    def __init__(self, state: MeetingState, storage: StorageService):
        self.state = state
        self.storage = storage
        self._last_processed = 0

    async def append_transcript(self, entry: TranscriptEntry) -> None:
        await self.storage.append_transcript_log(self.state.meeting_id, asdict(entry))

    def sync_from_log(self) -> list[TranscriptEntry]:
        log_entries = self.storage.load_transcript_log(self.state.meeting_id)
        if self._last_processed >= len(log_entries):
            return []

        new_items = log_entries[self._last_processed :]
        self._last_processed = len(log_entries)

        parsed_entries: list[TranscriptEntry] = []
        for item in new_items:
            parsed = TranscriptEntry(
                id=item.get("id", ""),
                timestamp=item.get("timestamp", ""),
                speaker=item.get("speaker", "Unknown"),
                text=item.get("text", ""),
                duration=item.get("duration", 0.0),
                confidence=item.get("confidence", 1.0),
            )
            parsed_entries.append(parsed)
            self.state.transcript.append(parsed)
            for participant in self.state.participants:
                if participant.name == parsed.speaker:
                    participant.speaking_count += 1
                    break

        return parsed_entries
