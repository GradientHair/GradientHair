from datetime import datetime
from pathlib import Path
from models.meeting import MeetingState


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

    def get_meeting_dir(self, meeting_id: str) -> Path:
        meeting_dir = self.base_path / meeting_id
        meeting_dir.mkdir(exist_ok=True)
        return meeting_dir

    def list_meetings(self) -> list[dict]:
        meetings: list[dict] = []
        for entry in self.base_path.iterdir():
            if not entry.is_dir():
                continue

            preparation_path = entry / "preparation.md"
            transcript_path = entry / "transcript.md"
            interventions_path = entry / "interventions.md"

            title = None
            scheduled_at = None
            if preparation_path.exists():
                try:
                    content = preparation_path.read_text(encoding="utf-8")
                    for line in content.splitlines():
                        if line.startswith("- **제목**:"):
                            title = line.split(":", 1)[1].strip()
                        elif line.startswith("- **일시**:"):
                            scheduled_at = line.split(":", 1)[1].strip()
                except OSError:
                    pass

            updated_at = None
            try:
                file_times = []
                for file in entry.iterdir():
                    if file.is_file():
                        file_times.append(file.stat().st_mtime)
                if file_times:
                    updated_at = datetime.fromtimestamp(max(file_times)).isoformat()
                else:
                    updated_at = datetime.fromtimestamp(entry.stat().st_mtime).isoformat()
            except OSError:
                updated_at = None

            meetings.append(
                {
                    "id": entry.name,
                    "title": title,
                    "scheduledAt": scheduled_at,
                    "updatedAt": updated_at,
                    "hasTranscript": transcript_path.exists(),
                    "hasInterventions": interventions_path.exists(),
                }
            )

        meetings.sort(key=lambda item: item.get("updatedAt") or "", reverse=True)
        return meetings

    def get_meeting_files(self, meeting_id: str) -> dict | None:
        meeting_dir = self.base_path / meeting_id
        if not meeting_dir.exists() or not meeting_dir.is_dir():
            return None

        def read_optional(path: Path) -> str | None:
            if not path.exists():
                return None
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return None

        return {
            "id": meeting_id,
            "preparation": read_optional(meeting_dir / "preparation.md"),
            "transcript": read_optional(meeting_dir / "transcript.md"),
            "interventions": read_optional(meeting_dir / "interventions.md"),
        }

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

    async def save_summary(self, state: MeetingState, content: str):
        meeting_dir = self.get_meeting_dir(state.meeting_id)
        with open(meeting_dir / "summary.md", "w", encoding="utf-8") as f:
            f.write(content)

    async def save_action_items(self, state: MeetingState, content: str):
        meeting_dir = self.get_meeting_dir(state.meeting_id)
        with open(meeting_dir / "action-items.md", "w", encoding="utf-8") as f:
            f.write(content)

    async def save_individual_feedback(self, state: MeetingState, feedback_by_participant: dict[str, str]):
        meeting_dir = self.get_meeting_dir(state.meeting_id)
        feedback_dir = meeting_dir / "feedback"
        feedback_dir.mkdir(exist_ok=True)
        for participant_name, content in feedback_by_participant.items():
            filename = self._safe_filename(participant_name) or "participant"
            with open(feedback_dir / f"{filename}.md", "w", encoding="utf-8") as f:
                f.write(content)

    def _safe_filename(self, name: str) -> str:
        safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
        return safe[:64]
