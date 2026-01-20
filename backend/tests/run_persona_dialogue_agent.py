#!/usr/bin/env python3
"""Run PersonaDialogueAgent with a sample meeting state."""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from agents.persona_dialogue_agent import PersonaDialogueAgent
from models.meeting import MeetingState, Participant, TranscriptEntry


def build_sample_state(agenda: str) -> MeetingState:
    meeting_id = f"demo_{uuid.uuid4().hex[:8]}"
    return MeetingState(
        meeting_id=meeting_id,
        title="Persona Demo Meeting",
        agenda=agenda,
        participants=[
            Participant(id="p1", name="김철수", role="Backend"),
            Participant(id="p2", name="이민수", role="Frontend"),
            Participant(id="p3", name="최지은", role="Design"),
        ],
        transcript=[
            TranscriptEntry(
                id="t1",
                timestamp="2026-01-20T10:00:00Z",
                speaker="김철수",
                text="이번 스프린트에서 무엇을 개선할지 논의해보죠.",
            )
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PersonaDialogueAgent")
    parser.add_argument("--agenda", default="스프린트 목표 및 업무 분담", help="회의 아젠다")
    parser.add_argument("--turns", type=int, default=3, help="생성할 발언 수")
    parser.add_argument("--off-topic", type=float, default=0.12, help="주제 이탈 확률")
    parser.add_argument("--agile-violation", type=float, default=0.1, help="애자일 위반 확률")
    parser.add_argument("--seed", type=int, default=None, help="랜덤 시드")
    parser.add_argument(
        "--llm-only",
        action="store_true",
        help="LLM 실모드만 사용 (OPENAI_API_KEY 필요)",
    )
    args = parser.parse_args()

    state = build_sample_state(args.agenda)
    agent = PersonaDialogueAgent(
        off_topic_rate=args.off_topic,
        agile_violation_rate=args.agile_violation,
    )

    turns = agent.generate_dialogue(
        state,
        recent_transcript=state.transcript,
        turns=args.turns,
        seed=args.seed,
        require_llm=args.llm_only,
    )

    for turn in turns:
        flags = []
        if turn.is_off_topic:
            flags.append("off_topic")
        if turn.is_agile_violation:
            flags.append("agile_violation")
        suffix = f" ({', '.join(flags)})" if flags else ""
        print(f"{turn.speaker}: {turn.text}{suffix}")


if __name__ == "__main__":
    main()
