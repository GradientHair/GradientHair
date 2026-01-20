from datetime import datetime
from pathlib import Path
from urllib.parse import unquote
import asyncio

from models.meeting import MeetingState, TranscriptEntry


class StorageService:
    def __init__(self, base_path: str | None = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Docker 환경: /app/meetings, 로컬 환경: 프로젝트 루트/meetings
            import os
            if os.path.exists("/app/meetings"):
                self.base_path = Path("/app/meetings")
            else:
                self.base_path = Path(__file__).parent.parent.parent / "meetings"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._transcript_buffers: dict[str, list[str]] = {}
        self._transcript_last_flush: dict[str, float] = {}
        self._buffer_flush_size = 10
        self._buffer_flush_interval = 2.0

    def _normalize_meeting_id(self, meeting_id: str) -> str:
        normalized = unquote(meeting_id)
        normalized = normalized.replace("/", "_").replace("\\", "_")
        normalized = normalized.strip()
        return normalized or meeting_id

    def get_meeting_dir(self, meeting_id: str) -> Path:
        normalized_id = self._normalize_meeting_id(meeting_id)
        meeting_dir = self.base_path / normalized_id
        legacy_dir = self.base_path / meeting_id
        if legacy_dir.exists() and not meeting_dir.exists():
            try:
                legacy_dir.rename(meeting_dir)
            except Exception:
                meeting_dir = legacy_dir
        meeting_dir.mkdir(exist_ok=True)
        return meeting_dir

    async def _flush_transcript_buffer(self, meeting_id: str) -> None:
        buffer = self._transcript_buffers.get(meeting_id)
        if not buffer:
            return
        meeting_dir = self.get_meeting_dir(meeting_id)
        with open(meeting_dir / "transcript_live.txt", "a", encoding="utf-8") as f:
            f.writelines(buffer)
        self._transcript_buffers[meeting_id] = []
        self._transcript_last_flush[meeting_id] = asyncio.get_event_loop().time()

    async def append_transcript_entry(self, state: MeetingState, entry: TranscriptEntry):
        time_str = entry.timestamp[:19].replace("T", " ")
        try:
            iso_ts = entry.timestamp.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(iso_ts)
            time_str = parsed.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

        latency_ms = f"{entry.latency_ms:.0f}ms" if entry.latency_ms is not None else "n/a"
        confidence = f"{entry.confidence:.2f}"
        line = f"[{time_str}] {entry.speaker} (conf={confidence}, latency={latency_ms}): {entry.text}\n"

        buffer = self._transcript_buffers.setdefault(state.meeting_id, [])
        buffer.append(line)

        now = asyncio.get_event_loop().time()
        last_flush = self._transcript_last_flush.get(state.meeting_id, 0.0)
        if len(buffer) >= self._buffer_flush_size or (now - last_flush) >= self._buffer_flush_interval:
            await self._flush_transcript_buffer(state.meeting_id)

    async def save_preparation(self, state: MeetingState):
        meeting_dir = self.get_meeting_dir(state.meeting_id)
        content = f"""# 회의 준비 자료

## 회의 정보
- **제목**: {state.title}
- **일시**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 참석자
| 이름 | 역할 |
|------|------|
"""
        for p in state.participants:
            content += f"| {p.name} | {p.role} |\n"

        content += f"\n## 아젠다\n{state.agenda}\n"

        with open(meeting_dir / "preparation.md", "w", encoding="utf-8") as f:
            f.write(content)

    async def save_transcript(self, state: MeetingState):
        await self._flush_transcript_buffer(state.meeting_id)
        meeting_dir = self.get_meeting_dir(state.meeting_id)
        content = f"""# 회의 녹취록

회의: {state.title}
일시: {state.started_at.strftime('%Y-%m-%d %H:%M') if state.started_at else 'N/A'}

---

"""
        for entry in state.transcript:
            time_str = entry.timestamp[:19].replace("T", " ")
            content += f"[{time_str}] **{entry.speaker}**: {entry.text}\n\n"

        with open(meeting_dir / "transcript.md", "w", encoding="utf-8") as f:
            f.write(content)

        # Plain text transcript for easy log-style consumption
        txt_lines: list[str] = []
        for entry in state.transcript:
            time_str = entry.timestamp[:19].replace("T", " ")
            try:
                # Handle ISO timestamps with timezone or Z
                iso_ts = entry.timestamp.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(iso_ts)
                time_str = parsed.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            txt_lines.append(f"[{time_str}] {entry.speaker}: {entry.text}")

        with open(meeting_dir / "transcript.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines) + ("\n" if txt_lines else ""))

    async def save_interventions(self, state: MeetingState):
        meeting_dir = self.get_meeting_dir(state.meeting_id)
        content = f"""# Agent 개입 기록

회의: {state.title}

---

"""
        for idx, inv in enumerate(state.interventions, 1):
            content += f"""## 개입 #{idx}
- **시간**: {inv.timestamp[:19].replace("T", " ")}
- **유형**: {inv.intervention_type.value}
- **메시지**: {inv.message}
"""
            if inv.violated_principle:
                content += f"- **위반 원칙**: {inv.violated_principle}\n"
            if inv.parking_lot_item:
                content += f"- **Parking Lot**: {inv.parking_lot_item}\n"
            content += "\n"

        with open(meeting_dir / "interventions.md", "w", encoding="utf-8") as f:
            f.write(content)
