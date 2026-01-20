"""Review agents - meeting-level evaluation and per-participant private feedback."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from models.meeting import MeetingState, Participant, TranscriptEntry, Intervention
from services.principles_service import PrinciplesService
from services.llm_validation import LLMStructuredOutputRunner, ValidationResult
from services.model_router import ModelRouter


@dataclass
class PrincipleContext:
    id: str
    name: str
    content: str


@dataclass
class PrincipleAssessment:
    id: str
    name: str
    score: int
    evidence: list[str]
    notes: str


@dataclass
class MeetingEvaluation:
    overall_score: int
    summary: str
    strengths: list[str]
    risks: list[str]
    recommendations: list[str]
    principle_assessments: list[PrincipleAssessment]
    action_items: list[dict]


@dataclass
class ParticipantFeedback:
    participant_id: str
    participant_name: str
    positives: list[str]
    improvements: list[str]
    private_notes: list[str]


@dataclass
class ReviewArtifacts:
    summary_markdown: str
    action_items_markdown: str
    feedback_by_participant: dict[str, str]


class ActionItemResponse(BaseModel):
    item: str = Field(...)
    owner: str = Field(default="")
    due: str = Field(default="")


class PrincipleAssessmentResponse(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    score: int = Field(..., ge=0, le=100)
    evidence: list[str] = Field(default_factory=list)
    notes: str = Field(default="")


class EvaluationResponse(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    summary: str = Field(default="")
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    principles: list[PrincipleAssessmentResponse] = Field(default_factory=list)
    action_items: list[ActionItemResponse] = Field(default_factory=list)


class ActionItemsResponse(BaseModel):
    items: list[ActionItemResponse] = Field(default_factory=list)


class ParticipantFeedbackResponse(BaseModel):
    positives: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    private_notes: list[str] = Field(default_factory=list)


class MeetingEvaluationAgent:
    """회의 전체가 원칙에 맞게 진행됐는지 평가하는 Agent."""

    def __init__(self):
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.max_retries = 2
        self.runner = None
        if self.client:
            choice = ModelRouter.select("reasoning", structured_output=True, api="chat")
            self.runner = LLMStructuredOutputRunner(
                client=self.client,
                model=choice.model,
                schema=EvaluationResponse,
                max_retries=self.max_retries,
                custom_validator=self._validate_evaluation_response,
            )

    async def analyze(
        self,
        state: MeetingState,
        principles: list[PrincipleContext],
    ) -> MeetingEvaluation:
        if not state.transcript:
            return self._fallback_evaluation(state, principles)

        if self.client is None:
            return self._fallback_evaluation(state, principles)

        try:
            prompt = self._build_prompt(state, principles)
            if self.runner is None:
                return self._fallback_evaluation(state, principles)
            parsed = self.runner.run(prompt)
            if parsed is None:
                return self._fallback_evaluation(state, principles)
            return self._parse_llm_response(parsed, principles, state)
        except Exception:
            return self._fallback_evaluation(state, principles)

    def _build_prompt(self, state: MeetingState, principles: list[PrincipleContext]) -> str:
        principles_text = "\n".join(
            [f"- {p.name}: {self._summarize_principle(p.content)}" for p in principles]
        )
        transcript_text = self._format_transcript(state.transcript, max_entries=25)
        interventions_text = self._format_interventions(state.interventions)
        participants_text = ", ".join([p.name for p in state.participants]) or "없음"
        index_text = self._build_transcript_index(state.transcript)
        context_text = self._format_action_item_context(state)

        return f"""당신은 회의 품질 리뷰어입니다. 회의가 원칙에 맞게 잘 진행되었는지 평가하세요.

회의 제목: {state.title}
참석자: {participants_text}

회의 컨텍스트(액션 아이템 작성 시 반드시 참고):
{context_text}

원칙:
{principles_text}

최근 대화 요약:
{transcript_text}

검색 인덱스(요약):
{index_text}

개입 기록:
{interventions_text}

JSON으로 응답하세요:
{{
  "overall_score": 0-100,
  "summary": "회의 요약 (2~4문장)",
  "strengths": ["강점1", "강점2"],
  "risks": ["리스크1", "리스크2"],
  "recommendations": ["개선 제안1", "개선 제안2"],
  "principles": [
    {{
      "id": "principle-id",
      "name": "원칙명",
      "score": 0-100,
      "evidence": ["근거1 (예: [03], [07])", "근거2"],
      "notes": "간단 설명"
    }}
  ],
  "action_items": [
    {{"item": "할 일", "owner": "담당자", "due": "기한(없으면 빈칸)"}}
  ]
}}
"""

    def _parse_llm_response(
        self,
        payload: EvaluationResponse,
        principles: list[PrincipleContext],
        state: MeetingState,
    ) -> MeetingEvaluation:
        principle_map = {p.id: p for p in principles}
        assessments: list[PrincipleAssessment] = []
        for item in payload.principles:
            p_id = item.id
            p_name = item.name
            if not p_name and p_id in principle_map:
                p_name = principle_map[p_id].name
            assessments.append(PrincipleAssessment(
                id=p_id or p_name,
                name=p_name or p_id,
                score=int(item.score),
                evidence=[str(e) for e in item.evidence],
                notes=str(item.notes),
            ))

        if not assessments:
            assessments = self._fallback_principle_assessments(state, principles)

        action_items = [a.model_dump() for a in payload.action_items]
        if not action_items:
            action_items = self._fallback_action_items(state)

        return MeetingEvaluation(
            overall_score=int(payload.overall_score),
            summary=str(payload.summary),
            strengths=[str(s) for s in payload.strengths],
            risks=[str(r) for r in payload.risks],
            recommendations=[str(r) for r in payload.recommendations],
            principle_assessments=assessments,
            action_items=action_items,
        )

    def _fallback_evaluation(
        self, state: MeetingState, principles: list[PrincipleContext]
    ) -> MeetingEvaluation:
        assessments = self._fallback_principle_assessments(state, principles)
        overall = int(sum(a.score for a in assessments) / len(assessments)) if assessments else 70
        interventions = len(state.interventions)
        summary = (
            f"총 발화 {len(state.transcript)}건, 개입 {interventions}회가 기록되었습니다. "
            "원칙 준수는 개입 기록을 기준으로 추정했습니다."
        )
        strengths = ["회의 기록이 정상적으로 수집되었습니다."]
        risks = []
        if interventions > 0:
            risks.append("원칙 위반 또는 주제 이탈 개입이 발생했습니다.")
        recommendations = ["회의 종료 전 원칙 준수 요약을 공유하세요."]
        action_items = self._fallback_action_items(state)
        return MeetingEvaluation(
            overall_score=overall,
            summary=summary,
            strengths=strengths,
            risks=risks,
            recommendations=recommendations,
            principle_assessments=assessments,
            action_items=action_items,
        )

    def _fallback_principle_assessments(
        self, state: MeetingState, principles: list[PrincipleContext]
    ) -> list[PrincipleAssessment]:
        assessments: list[PrincipleAssessment] = []
        for principle in principles:
            violations = [
                inv for inv in state.interventions
                if inv.violated_principle and principle.name in inv.violated_principle
            ]
            score = max(40, 100 - 20 * len(violations))
            evidence = [inv.message for inv in violations[:2]]
            notes = "개입 기록 기준 추정"
            assessments.append(PrincipleAssessment(
                id=principle.id,
                name=principle.name,
                score=score,
                evidence=evidence,
                notes=notes,
            ))
        if not assessments:
            assessments.append(PrincipleAssessment(
                id="general",
                name="회의 원칙",
                score=70,
                evidence=[],
                notes="원칙 정보 없음",
            ))
        return assessments

    def _fallback_action_items(self, state: MeetingState) -> list[dict]:
        if state.parking_lot:
            return [{"item": item, "owner": "", "due": ""} for item in state.parking_lot]
        return [{"item": "회의 요약 공유 및 후속 일정 확정", "owner": "", "due": ""}]

    def _format_transcript(self, transcript: list[TranscriptEntry], max_entries: int) -> str:
        recent = transcript[-max_entries:]
        lines = [
            f"[{idx:02d}] {t.timestamp} {t.speaker}: {t.text}"
            for idx, t in enumerate(recent, start=1)
        ]
        return "\n".join(lines) if lines else "내용 없음"

    def _format_interventions(self, interventions: list[Intervention]) -> str:
        if not interventions:
            return "개입 없음"
        lines = [
            f"- {inv.intervention_type.value}: {inv.message}"
            for inv in interventions[-10:]
        ]
        return "\n".join(lines)

    def _format_action_item_context(self, state: MeetingState) -> str:
        agenda = state.agenda.strip() if state.agenda else ""
        parking = ", ".join(state.parking_lot) if state.parking_lot else "없음"
        trigger_contexts = [
            inv.trigger_context
            for inv in state.interventions
            if inv.trigger_context
        ]
        trigger_summary = "; ".join(trigger_contexts[-5:]) if trigger_contexts else "없음"
        lines = [
            f"- 아젠다: {agenda or '없음'}",
            f"- Parking Lot: {parking}",
            f"- 개입 컨텍스트: {trigger_summary}",
        ]
        return "\n".join(lines)

    def _summarize_principle(self, content: str) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        bullets = [line for line in lines if line[0].isdigit() or line.startswith("-")]
        summary = ", ".join(bullets[:3]) if bullets else (lines[1] if len(lines) > 1 else lines[0])
        return summary[:200]

    def _build_transcript_index(self, transcript: list[TranscriptEntry]) -> str:
        if not transcript:
            return "데이터 없음"
        recent = transcript[-40:]
        chunks = [recent[i:i + 10] for i in range(0, len(recent), 10)]
        speaker_counts: dict[str, int] = {}
        keyword_counts: dict[str, int] = {}
        for entry in recent:
            speaker_counts[entry.speaker] = speaker_counts.get(entry.speaker, 0) + 1
            for token in entry.text.split():
                token = token.strip(".,!?\"'").lower()
                if len(token) < 2:
                    continue
                keyword_counts[token] = keyword_counts.get(token, 0) + 1
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        speaker_summary = ", ".join(f"{k}:{v}" for k, v in speaker_counts.items())
        keyword_summary = ", ".join(f"{k}:{v}" for k, v in top_keywords)
        chunk_summary = f"chunks:{len(chunks)}"
        return f"speakers({speaker_summary}), keywords({keyword_summary}), {chunk_summary}"

    def _validate_evaluation_response(self, parsed: EvaluationResponse) -> ValidationResult:
        if parsed.overall_score < 0 or parsed.overall_score > 100:
            return ValidationResult(ok=False, error="overall_score out of range")
        return ValidationResult(ok=True, value=parsed)


class ParticipantFeedbackAgent:
    """참석자별 개인 피드백 생성 Agent."""

    def __init__(self):
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.max_retries = 2
        self.runner = None
        if self.client:
            choice = ModelRouter.select("fast", structured_output=True, api="chat")
            self.runner = LLMStructuredOutputRunner(
                client=self.client,
                model=choice.model,
                schema=ParticipantFeedbackResponse,
                max_retries=self.max_retries,
                custom_validator=self._validate_feedback_response,
            )

    async def analyze(
        self,
        state: MeetingState,
        participant: Participant,
        transcript: list[TranscriptEntry],
    ) -> ParticipantFeedback:
        if self.client is None:
            return self._fallback_feedback(state, participant)

        try:
            prompt = self._build_prompt(state, participant, transcript)
            if self.runner is None:
                return self._fallback_feedback(state, participant)
            payload = self.runner.run(prompt)
            if payload is None:
                return self._fallback_feedback(state, participant)
            return ParticipantFeedback(
                participant_id=participant.id,
                participant_name=participant.name,
                positives=[str(v) for v in payload.positives],
                improvements=[str(v) for v in payload.improvements],
                private_notes=[str(v) for v in payload.private_notes],
            )
        except Exception:
            return self._fallback_feedback(state, participant)

    def _build_prompt(
        self,
        state: MeetingState,
        participant: Participant,
        transcript: list[TranscriptEntry],
    ) -> str:
        participant_lines = [
            f"{t.speaker}: {t.text}" for t in transcript if t.speaker == participant.name
        ][-8:]
        total = sum(p.speaking_count for p in state.participants) or 1
        share = round(participant.speaking_count / total * 100, 1)

        return f"""당신은 회의 코치입니다. 특정 참석자에게 개인 피드백을 제공합니다.

참석자: {participant.name} ({participant.role})
발언 비중: {share}%
최근 발화:
{chr(10).join(participant_lines) if participant_lines else '발화 기록 없음'}

JSON으로 응답하세요:
{{
  "positives": ["잘한 점1", "잘한 점2"],
  "improvements": ["개선점1", "개선점2"],
  "private_notes": ["비공개 메모1"]
}}
"""

    def _fallback_feedback(
        self,
        state: MeetingState,
        participant: Participant,
    ) -> ParticipantFeedback:
        total = sum(p.speaking_count for p in state.participants) or 1
        share = participant.speaking_count / total
        positives: list[str] = []
        improvements: list[str] = []
        private_notes: list[str] = []

        if share >= 0.5:
            positives.append("논의를 적극적으로 이끌었습니다.")
            improvements.append("발언 기회를 다른 참석자에게 더 나눠보세요.")
        elif share <= 0.1:
            improvements.append("핵심 의견을 더 자주 공유해 주세요.")
            positives.append("필요한 순간에 간결하게 참여했습니다.")
        else:
            positives.append("발언 비중이 균형적이었습니다.")
            improvements.append("원칙 준수 관점에서 추가 의견을 제시해 보세요.")

        private_notes.append("자동 생성 피드백(비공개)")

        return ParticipantFeedback(
            participant_id=participant.id,
            participant_name=participant.name,
            positives=positives,
            improvements=improvements,
            private_notes=private_notes,
        )

    def _validate_feedback_response(self, parsed: ParticipantFeedbackResponse) -> ValidationResult:
        if not parsed.positives and not parsed.improvements:
            return ValidationResult(ok=False, error="empty feedback")
        return ValidationResult(ok=True, value=parsed)


class ActionItemAgent:
    """회의 액션 아이템만 빠르게 추출하는 Agent."""

    def __init__(self):
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.max_retries = 1
        self.runner = None
        if self.client:
            choice = ModelRouter.select("fast", structured_output=True, api="chat")
            self.runner = LLMStructuredOutputRunner(
                client=self.client,
                model=choice.model,
                schema=ActionItemsResponse,
                max_retries=self.max_retries,
                custom_validator=self._validate_action_items_response,
            )

    async def analyze(self, state: MeetingState) -> list[dict]:
        if not state.transcript and not state.parking_lot:
            return self._fallback_action_items(state)
        if self.client is None or self.runner is None:
            return self._fallback_action_items(state)
        try:
            prompt = self._build_prompt(state)
            payload = self.runner.run(prompt)
            if payload is None:
                return self._fallback_action_items(state)
            items = [item.model_dump() for item in payload.items]
            return items or self._fallback_action_items(state)
        except Exception:
            return self._fallback_action_items(state)

    def _build_prompt(self, state: MeetingState) -> str:
        transcript_text = self._format_transcript(state.transcript, max_entries=20)
        interventions_text = self._format_interventions(state.interventions)
        participants_text = ", ".join([p.name for p in state.participants]) or "없음"
        context_text = self._format_action_item_context(state)
        return f"""당신은 회의에서 실행 가능한 Action Item을 빠르게 정리합니다.

회의 제목: {state.title}
참석자: {participants_text}

회의 컨텍스트:
{context_text}

최근 대화 요약:
{transcript_text}

개입 기록:
{interventions_text}

JSON으로 응답하세요:
{{
  "items": [
    {{"item": "할 일", "owner": "담당자", "due": "기한(없으면 빈칸)"}}
  ]
}}
"""

    def _fallback_action_items(self, state: MeetingState) -> list[dict]:
        if state.parking_lot:
            return [{"item": item, "owner": "", "due": ""} for item in state.parking_lot]
        return [{"item": "회의 요약 공유 및 후속 일정 확정", "owner": "", "due": ""}]

    def _validate_action_items_response(self, parsed: ActionItemsResponse) -> ValidationResult:
        if not parsed.items:
            return ValidationResult(ok=False, error="no action items")
        return ValidationResult(ok=True, value=parsed)

    def _format_transcript(self, transcript: list[TranscriptEntry], max_entries: int) -> str:
        recent = transcript[-max_entries:]
        lines = [
            f"[{idx:02d}] {t.timestamp} {t.speaker}: {t.text}"
            for idx, t in enumerate(recent, start=1)
        ]
        return "\n".join(lines) if lines else "내용 없음"

    def _format_interventions(self, interventions: list[Intervention]) -> str:
        if not interventions:
            return "개입 없음"
        lines = [
            f"- {inv.intervention_type.value}: {inv.message}"
            for inv in interventions[-6:]
        ]
        return "\n".join(lines)

    def _format_action_item_context(self, state: MeetingState) -> str:
        agenda = state.agenda.strip() if state.agenda else ""
        parking = ", ".join(state.parking_lot) if state.parking_lot else "없음"
        trigger_contexts = [
            inv.trigger_context
            for inv in state.interventions
            if inv.trigger_context
        ]
        trigger_summary = "; ".join(trigger_contexts[-3:]) if trigger_contexts else "없음"
        lines = [
            f"- 아젠다: {agenda or '없음'}",
            f"- Parking Lot: {parking}",
            f"- 개입 컨텍스트: {trigger_summary}",
        ]
        return "\n".join(lines)


class ReviewOrchestratorAgent:
    """회의 종료 전 리뷰 작업을 오케스트레이션하는 멀티 에이전트."""

    def __init__(self):
        self.evaluation_agent = MeetingEvaluationAgent()
        self.feedback_agent = ParticipantFeedbackAgent()
        self.action_item_agent = ActionItemAgent()
        self.principles_service = PrinciplesService()

    async def review(
        self,
        state: MeetingState,
        action_items: list[dict] | None = None,
        generate_action_items: bool = True,
    ) -> ReviewArtifacts:
        principles = self._load_principles(state)

        evaluation_task = asyncio.create_task(
            self.evaluation_agent.analyze(state, principles)
        )
        action_item_task = None
        if generate_action_items and action_items is None:
            action_item_task = asyncio.create_task(self.action_item_agent.analyze(state))
        feedback_tasks = [
            asyncio.create_task(
                self.feedback_agent.analyze(state, participant, state.transcript)
            )
            for participant in state.participants
        ]

        tasks = [evaluation_task]
        if action_item_task is not None:
            tasks.append(action_item_task)
        tasks.extend(feedback_tasks)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        evaluation: MeetingEvaluation
        evaluation = results[0] if isinstance(results[0], MeetingEvaluation) else None
        if evaluation is None:
            evaluation = self.evaluation_agent._fallback_evaluation(state, principles)

        if action_items is None and action_item_task is not None:
            action_result = results[1] if len(results) > 1 else None
            if isinstance(action_result, list):
                action_items = action_result
            else:
                action_items = self.action_item_agent._fallback_action_items(state)
        if action_items is None:
            action_items = evaluation.action_items or self.action_item_agent._fallback_action_items(state)

        feedbacks: list[ParticipantFeedback] = []
        feedback_start = 1 + (1 if action_item_task is not None else 0)
        for item in results[feedback_start:]:
            if isinstance(item, ParticipantFeedback):
                feedbacks.append(item)

        return ReviewArtifacts(
            summary_markdown=self._format_summary_markdown(state, evaluation),
            action_items_markdown=self._format_action_items(action_items),
            feedback_by_participant=self._format_feedback(feedbacks),
        )

    def _load_principles(self, state: MeetingState) -> list[PrincipleContext]:
        contexts: list[PrincipleContext] = []
        if state.principles:
            for p in state.principles:
                p_id = p.get("id", "")
                detail = self.principles_service.get_principle(p_id) if p_id else None
                if detail:
                    contexts.append(PrincipleContext(id=detail.id, name=detail.name, content=detail.content))
                else:
                    contexts.append(PrincipleContext(id=p_id or p.get("name", ""), name=p.get("name", ""), content=""))
        else:
            for p in self.principles_service.list_principles():
                contexts.append(PrincipleContext(id=p.id, name=p.name, content=p.content))
        return contexts

    def _format_summary_markdown(self, state: MeetingState, evaluation: MeetingEvaluation) -> str:
        lines = [
            "# 회의 요약",
            "",
            f"- 회의: {state.title}",
            f"- 참석자 수: {len(state.participants)}",
            f"- 총 발화: {len(state.transcript)}",
            f"- 개입 수: {len(state.interventions)}",
            "",
            "## 요약",
            evaluation.summary or "요약 정보를 생성하지 못했습니다.",
            "",
            "## 원칙 준수 평가",
            f"- 종합 점수: {evaluation.overall_score}",
        ]
        for assessment in evaluation.principle_assessments:
            lines.append(f"  - {assessment.name}: {assessment.score} ({assessment.notes})")
            if assessment.evidence:
                lines.append(f"    - 근거: {', '.join(assessment.evidence)}")

        if evaluation.strengths:
            lines.extend(["", "## 강점"] + [f"- {s}" for s in evaluation.strengths])
        if evaluation.risks:
            lines.extend(["", "## 리스크"] + [f"- {r}" for r in evaluation.risks])
        if evaluation.recommendations:
            lines.extend(["", "## 개선 제안"] + [f"- {r}" for r in evaluation.recommendations])

        return "\n".join(lines) + "\n"

    def _format_action_items(self, action_items: list[dict]) -> str:
        lines = ["# Action Items", ""]
        if not action_items:
            lines.append("추출된 Action Item이 없습니다.")
            return "\n".join(lines) + "\n"

        for item in action_items:
            task = item.get("item", "")
            owner = item.get("owner", "") or "-"
            due = item.get("due", "") or "-"
            lines.append(f"- [ ] {task} | Owner: {owner} | Due: {due}")
        return "\n".join(lines) + "\n"

    def _format_feedback(self, feedbacks: list[ParticipantFeedback]) -> dict[str, str]:
        result: dict[str, str] = {}
        for feedback in feedbacks:
            lines = [
                f"# 개인 피드백: {feedback.participant_name}",
                "",
                "## 잘한 점",
            ]
            lines.extend([f"- {p}" for p in feedback.positives] or ["- (없음)"])
            lines.extend(["", "## 개선하면 좋을 점"])
            lines.extend([f"- {i}" for i in feedback.improvements] or ["- (없음)"])
            lines.extend(["", "## 비공개 메모"])
            lines.extend([f"- {n}" for n in feedback.private_notes] or ["- (없음)"])
            result[feedback.participant_name] = "\n".join(lines) + "\n"
        return result
