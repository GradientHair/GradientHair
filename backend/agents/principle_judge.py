"""
PrincipleJudge: Analyzes transcript for principle violations and modifies context.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.meeting_context import MeetingContext, PrincipleViolation
    from models.meeting import TranscriptEntry

logger = logging.getLogger(__name__)


class PrincipleJudge:
    """
    Judge agent that analyzes principle violations.
    Modifies context.principle_violations based on analysis.
    """

    def __init__(self):
        # Heuristic patterns for common violations
        self.violation_patterns = {
            "unilateral_decision": {
                "keywords": ["내가 결정할게", "제가 정하겠습니다", "그냥 이렇게 하자", "내 말대로"],
                "principle": "수평적 의사결정",
                "reason": "일방적인 의사결정 감지",
            },
            "time_pressure": {
                "keywords": ["빨리 빨리", "시간 없어", "그냥 넘어가자", "나중에 하자"],
                "principle": "타임박스 준수",
                "reason": "시간 압박으로 인한 성급한 결정",
            },
            "dismissive": {
                "keywords": ["그건 안돼", "그건 별로", "그건 아니지", "무슨 소리야"],
                "principle": "심리적 안전",
                "reason": "의견 무시 또는 비하 감지",
            },
            "scope_creep": {
                "keywords": ["이것도 하고", "저것도 추가", "더 넣자", "확장하자"],
                "principle": "스코프 관리",
                "reason": "범위 확장 시도 감지",
            },
        }

    async def analyze(
        self,
        context: "MeetingContext",
        recent_transcript: list["TranscriptEntry"],
    ) -> None:
        """
        Analyze transcript for principle violations and update context.
        """
        from agents.meeting_context import PrincipleViolation

        if not recent_transcript:
            return

        latest_entry = recent_transcript[-1]
        latest_text = latest_entry.text.lower() if latest_entry.text else ""

        # Check each violation pattern
        for violation_id, pattern in self.violation_patterns.items():
            if any(kw in latest_text for kw in pattern["keywords"]):
                violation = PrincipleViolation(
                    principle_id=violation_id,
                    principle_name=pattern["principle"],
                    violation_reason=pattern["reason"],
                    speaker=latest_entry.speaker,
                    timestamp=latest_entry.timestamp,
                    severity=0.7,
                )

                # Avoid duplicates (same speaker, same violation within recent entries)
                existing = [
                    v for v in context.principle_violations
                    if v.principle_id == violation_id
                    and v.speaker == latest_entry.speaker
                ]
                if not existing:
                    old_count = len(context.principle_violations)
                    context.principle_violations.append(violation)
                    context.add_issue(
                        f"원칙 위반 ({pattern['principle']}): {pattern['reason']} - {latest_entry.speaker}"
                    )
                    logger.info(f"[PrincipleJudge] *** CONTEXT CHANGED ***")
                    logger.info(f"[PrincipleJudge]   principle_violations count: {old_count} → {len(context.principle_violations)}")
                    logger.info(f"[PrincipleJudge]   violation: {pattern['principle']} by {latest_entry.speaker}")
                    logger.info(f"[PrincipleJudge]   reason: {pattern['reason']}")

        # Keep only recent violations (last 5)
        if len(context.principle_violations) > 5:
            context.principle_violations = context.principle_violations[-5:]
