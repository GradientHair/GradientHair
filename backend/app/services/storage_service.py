from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.core.config import settings


class StorageService:
    def __init__(self, base_path: str | None = None) -> None:
        self.base_path = Path(base_path or settings.storage_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def meeting_dir(self, meeting_id: str) -> Path:
        path = self.base_path / meeting_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_preparation(self, meeting_id: str, title: str, agenda: str, participants: list[dict]) -> Path:
        content = [
            "# 회의 준비 자료",
            "",
            "## 회의 정보",
            f"- **제목**: {title}",
            f"- **일시**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "- **상태**: preparing",
            "",
            "## 참석자",
            "| 이름 | 역할 |",
            "|------|------|",
        ]
        for participant in participants:
            content.append(f"| {participant.get('name')} | {participant.get('role', '')} |")
        content.extend(["", "## 아젠다", agenda.strip(), ""])

        path = self.meeting_dir(meeting_id) / "preparation.md"
        path.write_text("\n".join(content), encoding="utf-8")
        return path

    def save_transcript(self, meeting_id: str, title: str, transcript: list[dict]) -> Path:
        lines = [
            "# 회의 녹취록",
            "",
            f"회의: {title}",
            f"일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
        ]
        for entry in transcript:
            timestamp = entry.get("timestamp", "")
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "")
            lines.append(f"[{timestamp}] **{speaker}**: {text}")
            lines.append("")
        path = self.meeting_dir(meeting_id) / "transcript.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def save_interventions(self, meeting_id: str, title: str, interventions: list[dict]) -> Path:
        lines = [
            "# Agent 개입 기록",
            "",
            f"회의: {title}",
            f"생성일: {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "---",
            "",
        ]
        for idx, intervention in enumerate(interventions, 1):
            lines.append(f"## 개입 #{idx}")
            lines.append(f"- **시간**: {intervention.get('timestamp', '')}")
            lines.append(f"- **유형**: {intervention.get('type', '')}")
            lines.append(f"- **메시지**: {intervention.get('message', '')}")
            if intervention.get("metadata"):
                lines.append(f"- **메타데이터**: {intervention.get('metadata')}")
            lines.append("")
        path = self.meeting_dir(meeting_id) / "interventions.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def save_summary(self, meeting_id: str, title: str, summary: str) -> Path:
        lines = [
            "# 회의 요약",
            "",
            f"회의: {title}",
            f"생성일: {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "---",
            "",
            summary,
            "",
        ]
        path = self.meeting_dir(meeting_id) / "summary.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def save_action_items(self, meeting_id: str, title: str, items: list[dict]) -> Path:
        lines = [
            "# Action Items",
            "",
            f"회의: {title}",
            f"생성일: {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "---",
            "",
            "## 할당된 업무",
            "",
        ]
        for idx, item in enumerate(items, 1):
            lines.append(f"### {idx}. {item.get('description', '')}")
            lines.append(f"- **담당**: {item.get('assignee', '미정')}")
            if item.get("dueDate"):
                lines.append(f"- **기한**: {item.get('dueDate')}")
            if item.get("context"):
                lines.append(f"- **맥락**: {item.get('context')}")
            lines.append("")
        path = self.meeting_dir(meeting_id) / "action-items.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
