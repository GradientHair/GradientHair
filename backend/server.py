import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from models.meeting import MeetingState, MeetingStatus, Participant, TranscriptEntry
from services.realtime_stt_service import (
    RealtimeSTTService,
    STTConnectionError,
    STTConfigurationError,
    ConnectionState,
)
from services.speaker_service import SpeakerService
from services.storage_service import StorageService
from services.speech_stt_service import SpeechSTTService, DiarizedSegment
from services.principles_service import (
    PrinciplesService,
    Principle,
    PrincipleDetail,
    PrincipleCreate,
    PrincipleUpdate,
    PrincipleCreateResponse,
)
from agents.review_agent import ReviewOrchestratorAgent
from agents.safety_orchestrator import SafetyOrchestrator
from agents.persona_dialogue_agent import PersonaDialogueAgent
from agents.meeting_context import MeetingContext, AgentOrchestrator
from i18n import pick

app = FastAPI(title="MeetingMod API")

# Get CORS origins from environment variable, default to localhost:3000
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state store
meetings: Dict[str, MeetingState] = {}


class CreateMeetingRequest(BaseModel):
    title: str
    agenda: str
    participants: list[dict]
    principleIds: list[str]


class TranscriptEntryRequest(BaseModel):
    id: str
    timestamp: str
    speaker: str
    text: str
    latencyMs: float | None = None


class InterventionRequest(BaseModel):
    id: str
    type: str
    message: str
    timestamp: str
    violatedPrinciple: str | None = None
    parkingLotItem: str | None = None


class SaveMeetingRequest(BaseModel):
    title: str
    agenda: str
    participants: list[dict]
    transcript: list[TranscriptEntryRequest]
    interventions: list[InterventionRequest]
    speakerStats: dict


# Response models
class ParticipantResponse(BaseModel):
    id: str
    name: str
    role: str
    speakingTime: float
    speakingCount: int


class TranscriptEntryResponse(BaseModel):
    id: str
    timestamp: str
    speaker: str
    text: str
    duration: float
    confidence: float
    latencyMs: float | None


class InterventionResponse(BaseModel):
    id: str
    timestamp: str
    type: str
    message: str
    triggerContext: str
    violatedPrinciple: str | None
    parkingLotItem: str | None
    suggestedSpeaker: str | None


class SpeakerStatsEntry(BaseModel):
    percentage: float
    speakingTime: float
    count: int


class MeetingResponse(BaseModel):
    id: str
    title: str
    status: str
    agenda: str
    principles: list[dict]
    participants: list[ParticipantResponse]
    transcript: list[TranscriptEntryResponse]
    interventions: list[InterventionResponse]
    parkingLot: list[str]
    speakerStats: dict[str, SpeakerStatsEntry]
    startedAt: str | None
    endedAt: str | None


class MeetingStartResponse(BaseModel):
    id: str
    status: str
    startedAt: str


class ErrorResponse(BaseModel):
    detail: str


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}


class InjectTranscriptEntry(BaseModel):
    text: str
    speaker: str | None = None
    timestamp: str | None = None
    confidence: float | None = None


class InjectTranscriptRequest(BaseModel):
    entries: list[InjectTranscriptEntry]
    runAgents: bool = True
    sendFrontend: bool = True


from fastapi.responses import HTMLResponse

@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """Serve audio test page"""
    try:
        with open("test_audio.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Test page not found</h1>"


@app.post("/api/v1/meetings")
async def create_meeting(request: CreateMeetingRequest):
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    meeting_id = f"{timestamp}-{request.title.lower().replace(' ', '-')}"

    participants = [
        Participant(id=p.get("id", str(uuid.uuid4())), name=p["name"], role=p["role"])
        for p in request.participants
    ]

    # 원칙 로드 (간단히 하드코딩)
    principles = []
    if "agile" in request.principleIds:
        principles.append({"id": "agile", "name": pick("수평적 의사결정", "Shared decision-making")})
        principles.append({"id": "agile", "name": pick("타임박스", "Timebox")})
    if "aws-leadership" in request.principleIds:
        principles.append({"id": "aws", "name": "Disagree and Commit"})

    state = MeetingState(
        meeting_id=meeting_id,
        title=request.title,
        agenda=request.agenda,
        participants=participants,
        principles=principles,
    )

    meetings[meeting_id] = state

    storage = StorageService()
    await storage.save_preparation(state)

    return {"id": meeting_id, "status": "preparing"}


@app.post("/api/v1/meetings/{meeting_id}/inject_transcript")
async def inject_transcript(meeting_id: str, request: InjectTranscriptRequest):
    """Inject transcript entries and optionally run agents (E2E verification)."""
    state = meetings.get(meeting_id)
    if not state:
        state = MeetingState(
            meeting_id=meeting_id,
            title=meeting_id,
            participants=[],
            principles=[],
        )
        meetings[meeting_id] = state

    storage = StorageService()
    safety_orchestrator = SafetyOrchestrator()

    appended = 0
    for entry in request.entries:
        if not entry.text:
            continue
        speaker = entry.speaker or "Injected"
        for p in state.participants:
            if p.name == speaker:
                p.speaking_count += 1
                break
        transcript_entry = TranscriptEntry(
            id=f"tr_{uuid.uuid4().hex[:8]}",
            timestamp=entry.timestamp or datetime.utcnow().isoformat(),
            speaker=speaker,
            text=entry.text,
            confidence=entry.confidence or 0.0,
            latency_ms=0.0,
        )
        state.transcript.append(transcript_entry)
        await storage.append_transcript_entry(state, transcript_entry)
        appended += 1
        if request.sendFrontend:
            await manager.send_message(
                meeting_id, {"type": "transcript", "data": transcript_entry.__dict__}
            )

    intervention_payload = None
    if request.runAgents and state.transcript:
        result = await safety_orchestrator.analyze(state, state.transcript[-10:])
        intervention = result.intervention
        if result.errors:
            logger.warning(f"[{meeting_id}] Agent errors: {[e.error for e in result.errors]}")
        if result.warnings:
            logger.warning(f"[{meeting_id}] Safety warnings: {result.warnings}")

        if intervention:
            state.interventions.append(intervention)
            if intervention.parking_lot_item:
                state.parking_lot.append(intervention.parking_lot_item)
            await storage.save_interventions(state)
            intervention_payload = {
                "id": intervention.id,
                "type": intervention.intervention_type.value,
                "message": intervention.message,
                "timestamp": intervention.timestamp,
                "violatedPrinciple": intervention.violated_principle,
                "parkingLotItem": intervention.parking_lot_item,
            }
            if request.sendFrontend:
                await manager.send_message(
                    meeting_id, {"type": "intervention", "data": intervention_payload}
                )

    return {"status": "ok", "appended": appended, "intervention": intervention_payload}


def _build_speaker_stats(state: MeetingState) -> dict[str, SpeakerStatsEntry]:
    """Build speaker statistics from meeting state."""
    total = sum(p.speaking_count for p in state.participants)
    stats = {}
    for p in state.participants:
        percentage = round(p.speaking_count / total * 100, 1) if total > 0 else 0.0
        stats[p.name] = SpeakerStatsEntry(
            percentage=percentage,
            speakingTime=p.speaking_time,
            count=p.speaking_count,
        )
    return stats


def _meeting_state_to_response(state: MeetingState) -> MeetingResponse:
    """Convert MeetingState dataclass to MeetingResponse."""
    participants = [
        ParticipantResponse(
            id=p.id,
            name=p.name,
            role=p.role,
            speakingTime=p.speaking_time,
            speakingCount=p.speaking_count,
        )
        for p in state.participants
    ]

    transcript = [
        TranscriptEntryResponse(
            id=t.id,
            timestamp=t.timestamp,
            speaker=t.speaker,
            text=t.text,
            duration=t.duration,
            confidence=t.confidence,
            latencyMs=t.latency_ms,
        )
        for t in state.transcript
    ]

    interventions = [
        InterventionResponse(
            id=i.id,
            timestamp=i.timestamp,
            type=i.intervention_type.value,
            message=i.message,
            triggerContext=i.trigger_context,
            violatedPrinciple=i.violated_principle,
            parkingLotItem=i.parking_lot_item,
            suggestedSpeaker=i.suggested_speaker,
        )
        for i in state.interventions
    ]

    return MeetingResponse(
        id=state.meeting_id,
        title=state.title,
        status=state.status.value,
        agenda=state.agenda,
        principles=state.principles,
        participants=participants,
        transcript=transcript,
        interventions=interventions,
        parkingLot=state.parking_lot,
        speakerStats=_build_speaker_stats(state),
        startedAt=state.started_at.isoformat() if state.started_at else None,
        endedAt=state.ended_at.isoformat() if state.ended_at else None,
    )


@app.get("/api/v1/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: str):
    """Get meeting details by ID."""
    state = meetings.get(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return _meeting_state_to_response(state)


@app.post("/api/v1/meetings/{meeting_id}/start", response_model=MeetingStartResponse)
async def start_meeting(meeting_id: str):
    """Start a meeting - changes status to IN_PROGRESS and sets startedAt timestamp."""
    state = meetings.get(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if state.status == MeetingStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Meeting is already in progress")

    if state.status == MeetingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Meeting has already completed")

    state.status = MeetingStatus.IN_PROGRESS
    state.started_at = datetime.utcnow()

    return MeetingStartResponse(
        id=state.meeting_id,
        status=state.status.value,
        startedAt=state.started_at.isoformat(),
    )


async def _run_review_jobs(state: MeetingState) -> None:
    storage = StorageService()
    try:
        review_agent = ReviewOrchestratorAgent()
        action_items_task = asyncio.create_task(review_agent.action_item_agent.analyze(state))

        async def _save_action_items():
            items = await action_items_task
            content = review_agent._format_action_items(items)
            await storage.save_action_items(state, content)
            return items

        save_action_items_task = asyncio.create_task(_save_action_items())
        review = await review_agent.review(state, generate_action_items=False)
        await storage.save_summary(state, review.summary_markdown)
        await storage.save_individual_feedback(state, review.feedback_by_participant)
        await save_action_items_task
    except Exception as e:
        logger.error(f"Review generation failed: {e}", exc_info=True)


async def _run_diarize_job(state: MeetingState) -> None:
    storage = StorageService()
    pcm_path = storage.get_audio_pcm_path(state.meeting_id)
    if not pcm_path.exists() or pcm_path.stat().st_size == 0:
        return
    service = SpeechSTTService()
    if not service.enabled:
        return
    try:
        pcm_bytes = await asyncio.to_thread(pcm_path.read_bytes)
        segments = await asyncio.to_thread(service.transcribe_pcm_bytes, pcm_bytes)
        if not segments:
            return
        meeting_dir = storage.get_meeting_dir(state.meeting_id)
        diarized_md = meeting_dir / "transcript_diarized.md"
        diarized_json = meeting_dir / "transcript_diarized.json"
        lines = [f"# Diarized Transcript\n\n{pick('회의', 'Meeting')}: {state.title}\n\n---\n"]
        for seg in segments:
            lines.append(f"- **{seg.speaker}**: {seg.text}\n")
        diarized_md.write_text("".join(lines), encoding="utf-8")
        diarized_json.write_text(
            json.dumps([seg.__dict__ for seg in segments], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error(f"Diarize transcription failed: {e}", exc_info=True)


@app.post("/api/v1/meetings/{meeting_id}/end")
async def end_meeting(meeting_id: str):
    state = meetings.get(meeting_id)
    if not state:
        return {"error": "Meeting not found"}

    state.status = MeetingStatus.COMPLETED
    state.ended_at = datetime.utcnow()

    storage = StorageService()
    await storage.save_transcript(state)
    await storage.save_interventions(state)
    asyncio.create_task(_run_review_jobs(state))
    asyncio.create_task(_run_diarize_job(state))

    return {"id": meeting_id, "status": "completed", "reviewStatus": "queued"}


@app.post("/api/v1/meetings/{meeting_id}/save")
async def save_meeting(meeting_id: str, request: SaveMeetingRequest):
    """에이전트/오프라인 모드에서 프론트엔드 데이터를 저장"""
    from models.meeting import Intervention, InterventionType

    participants = [
        Participant(id=p.get("id", str(uuid.uuid4())), name=p["name"], role=p["role"])
        for p in request.participants
    ]

    transcript = [
        TranscriptEntry(
            id=t.id,
            timestamp=t.timestamp,
            speaker=t.speaker,
            text=t.text,
            latency_ms=t.latencyMs,
        )
        for t in request.transcript
    ]

    interventions = [
        Intervention(
            id=i.id,
            timestamp=i.timestamp,
            intervention_type=InterventionType(i.type),
            message=i.message,
            violated_principle=i.violatedPrinciple,
            parking_lot_item=i.parkingLotItem,
        )
        for i in request.interventions
    ]

    state = MeetingState(
        meeting_id=meeting_id,
        title=request.title,
        agenda=request.agenda,
        participants=participants,
        transcript=transcript,
        interventions=interventions,
        status=MeetingStatus.COMPLETED,
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
    )

    storage = StorageService()
    await storage.save_preparation(state)
    await storage.save_transcript(state)
    await storage.save_interventions(state)
    asyncio.create_task(_run_review_jobs(state))
    asyncio.create_task(_run_diarize_job(state))

    return {"id": meeting_id, "status": "saved", "reviewStatus": "queued", "files": [
        f"meetings/{meeting_id}/preparation.md",
        f"meetings/{meeting_id}/transcript.md",
        f"meetings/{meeting_id}/interventions.md",
        f"meetings/{meeting_id}/summary.md",
        f"meetings/{meeting_id}/action-items.md",
        f"meetings/{meeting_id}/feedback/",
    ]}


# ============================================================================
# Principles API Endpoints
# ============================================================================

# Initialize principles service
principles_service = PrinciplesService()


class PrinciplesListResponse(BaseModel):
    principles: list[Principle]

class MeetingListItem(BaseModel):
    id: str
    title: str | None
    scheduledAt: str | None
    updatedAt: str | None
    hasTranscript: bool
    hasInterventions: bool


class MeetingListResponse(BaseModel):
    meetings: list[MeetingListItem]

class MeetingFilesResponse(BaseModel):
    id: str
    preparation: str | None
    transcript: str | None
    interventions: str | None
    summary: str | None = None
    actionItems: str | None = None


@app.get("/api/v1/meetings", response_model=MeetingListResponse)
async def list_meetings():
    storage = StorageService()
    meetings = storage.list_meetings()
    return MeetingListResponse(meetings=meetings)


@app.get("/api/v1/meetings/{meeting_id}/files", response_model=MeetingFilesResponse)
async def get_meeting_files(meeting_id: str):
    storage = StorageService()
    files = storage.get_meeting_files(meeting_id)
    if not files:
        raise HTTPException(status_code=404, detail="Meeting files not found")
    return files


@app.get("/api/v1/principles", response_model=PrinciplesListResponse)
async def list_principles():
    """
    List all principles from the principles/ directory.

    Returns a list of all available meeting principles with their content.
    """
    principles = principles_service.list_principles()
    return PrinciplesListResponse(principles=principles)


@app.get("/api/v1/principles/{principle_id}", response_model=PrincipleDetail)
async def get_principle(principle_id: str):
    """
    Get a single principle by ID.

    Args:
        principle_id: The unique identifier of the principle (filename without .md extension)

    Returns:
        The principle details including id, name, and content.

    Raises:
        404: If the principle is not found.
    """
    principle = principles_service.get_principle(principle_id)
    if not principle:
        raise HTTPException(
            status_code=404,
            detail=f"Principle '{principle_id}' not found"
        )
    return principle


@app.put("/api/v1/principles/{principle_id}", response_model=PrincipleDetail)
async def update_principle(principle_id: str, update: PrincipleUpdate):
    """
    Update an existing principle.

    Args:
        principle_id: The unique identifier of the principle
        update: The update payload containing optional name and/or content

    Returns:
        The updated principle details.

    Raises:
        404: If the principle is not found.
        400: If the update failed.
    """
    updated = principles_service.update_principle(principle_id, update)
    if not updated:
        # Check if the principle exists
        existing = principles_service.get_principle(principle_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Principle '{principle_id}' not found"
            )
        raise HTTPException(
            status_code=400,
            detail="Failed to update principle"
        )
    return updated


@app.post("/api/v1/principles", response_model=PrincipleCreateResponse, status_code=201)
async def create_principle(create: PrincipleCreate):
    """
    Create a new custom principle.

    Args:
        create: The principle creation payload with name and content

    Returns:
        The created principle info including generated id and file path.

    Raises:
        400: If the principle creation failed.
    """
    result = principles_service.create_principle(create)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Failed to create principle"
        )
    return result


@app.delete("/api/v1/principles/{principle_id}", status_code=204)
async def delete_principle(principle_id: str):
    """
    Delete a principle by ID.

    Args:
        principle_id: The unique identifier of the principle

    Raises:
        404: If the principle is not found.
    """
    deleted = principles_service.delete_principle(principle_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Principle '{principle_id}' not found"
        )
    return Response(status_code=204)


# ============================================================================
# WebSocket Connection Manager
# ============================================================================


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, meeting_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[meeting_id] = websocket

    def disconnect(self, meeting_id: str):
        if meeting_id in self.active_connections:
            del self.active_connections[meeting_id]

    async def send_message(self, meeting_id: str, message: dict):
        if meeting_id in self.active_connections:
            try:
                await self.active_connections[meeting_id].send_json(message)
            except WebSocketDisconnect:
                self.disconnect(meeting_id)
            except Exception as e:
                logger.error(f"Failed to send websocket message: {e}", exc_info=True)
                self.disconnect(meeting_id)


manager = ConnectionManager()


@app.websocket("/ws/meetings/{meeting_id}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str):
    logger.info(f"WebSocket endpoint called for meeting: {meeting_id}")
    try:
        await manager.connect(meeting_id, websocket)
        logger.info(f"WebSocket connected for meeting: {meeting_id}")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket: {e}", exc_info=True)
        return
    mode = (websocket.query_params.get("mode") or "audio").lower()
    stt_enabled = mode != "agent"
    logger.info(f"[{meeting_id}] Meeting mode: {mode} (stt_enabled={stt_enabled})")

    state = meetings.get(meeting_id)
    if not state:
        # 새 회의 상태 생성 (데모용)
        state = MeetingState(
            meeting_id=meeting_id,
            title=meeting_id,
            participants=[],
            principles=[],
        )
        meetings[meeting_id] = state

    state.status = MeetingStatus.IN_PROGRESS
    state.started_at = datetime.utcnow()

    stt_service = RealtimeSTTService()
    speaker_service = SpeakerService()
    speaker_service.set_participants(state.participants)
    safety_orchestrator = SafetyOrchestrator()
    storage = StorageService()
    persona_agent = PersonaDialogueAgent(stream=False)
    agent_mode_task: asyncio.Task | None = None
    agent_mode_enabled = False
    speaker_stats_applied: set[str] = set()
    pending_transcripts: dict[str, TranscriptEntry] = {}
    pending_speech_end = False
    last_agent_run_at = 0.0
    last_partial_sent_at: dict[str, float] = {}

    # New agent orchestration context
    meeting_context = MeetingContext(meeting_state=state)

    async def send_intervention_ws(intervention):
        """Send intervention via WebSocket."""
        try:
            await manager.send_message(
                meeting_id,
                {
                    "type": "intervention",
                    "data": {
                        "id": intervention.id,
                        "type": intervention.intervention_type.value,
                        "message": intervention.message,
                        "timestamp": intervention.timestamp,
                        "violatedPrinciple": intervention.violated_principle,
                        "parkingLotItem": intervention.parking_lot_item,
                        "suggestedSpeaker": intervention.suggested_speaker,
                    },
                },
            )
            state.interventions.append(intervention)
            logger.info(f"[{meeting_id}] Sent intervention: {intervention.message}")
        except Exception as e:
            logger.error(f"[{meeting_id}] Failed to send intervention: {e}")

    agent_orchestrator = AgentOrchestrator(send_intervention=send_intervention_ws)

    def _coerce_participants(raw_participants: list[dict], existing: list[Participant]) -> list[Participant]:
        existing_by_id = {p.id: p for p in existing}
        existing_by_name = {p.name: p for p in existing}
        updated: list[Participant] = []

        for raw in raw_participants:
            name = raw.get("name")
            if not name:
                continue
            role = raw.get("role", "")
            participant_id = raw.get("id") or str(uuid.uuid4())
            existing_participant = existing_by_id.get(participant_id) or existing_by_name.get(name)
            if existing_participant:
                existing_participant.id = participant_id
                existing_participant.name = name
                existing_participant.role = role
                updated.append(existing_participant)
            else:
                updated.append(Participant(id=participant_id, name=name, role=role))

        return updated

    def _apply_speaker_stats(entry: TranscriptEntry, speaker: str) -> bool:
        if entry.id in speaker_stats_applied:
            return False
        if not speaker or speaker == "Unknown":
            return False
        for p in state.participants:
            if p.name == speaker:
                p.speaking_count += 1
                speaker_stats_applied.add(entry.id)
                return True
        return False

    async def _send_speaker_stats():
        total = sum(p.speaking_count for p in state.participants)
        if total <= 0:
            return
        stats = {
            p.name: {
                "percentage": round(p.speaking_count / total * 100),
                "speakingTime": p.speaking_time,
                "count": p.speaking_count,
            }
            for p in state.participants
        }
        await manager.send_message(
            meeting_id, {"type": "speaker_stats", "data": {"stats": stats}}
        )

    async def maybe_run_agents():
        nonlocal last_agent_run_at
        now = asyncio.get_event_loop().time()
        if now - last_agent_run_at < 1.0:
            return
        last_agent_run_at = now
        await run_agents()

    async def _enrich_transcript(entry: TranscriptEntry) -> None:
        speaker = entry.speaker
        confidence = entry.confidence
        normalized_text = entry.text
        if state.participants:
            try:
                result = await speaker_service.identify_speaker(entry.text)
                speaker = result.get("speaker", "Unknown")
                confidence = float(result.get("confidence", 0.0))
                normalized_text = result.get("text", result.get("text_ko", entry.text))
            except Exception as e:
                logger.error(f"Speaker identification failed: {e}", exc_info=True)
                speaker = "Unknown"
                confidence = 0.0
                normalized_text = entry.text
        else:
            try:
                normalized_text = await speaker_service.normalize_text(entry.text)
            except Exception as e:
                logger.error(f"Text normalization failed: {e}", exc_info=True)
                normalized_text = entry.text

        participant_names = {p.name for p in state.participants}
        if speaker not in participant_names and confidence < 0.5:
            speaker = "Unknown"
            confidence = 0.0

        if speaker == entry.speaker and normalized_text == entry.text and confidence == entry.confidence:
            return

        entry.speaker = speaker
        entry.text = normalized_text
        entry.confidence = confidence

        try:
            await manager.send_message(
                meeting_id,
                {
                    "type": "transcript_update",
                    "data": {
                        "id": entry.id,
                        "speaker": entry.speaker,
                        "text": entry.text,
                        "confidence": entry.confidence,
                    },
                },
            )
        except Exception as e:
            logger.warning(f"[{meeting_id}] Failed to send transcript update: {e}")

        if _apply_speaker_stats(entry, entry.speaker):
            try:
                await _send_speaker_stats()
            except Exception as e:
                logger.warning(f"[{meeting_id}] Failed to send speaker stats: {e}")

    async def add_partial_transcript(item_id: str, text: str) -> None:
        nonlocal pending_speech_end
        if not item_id:
            return
        text = (text or "").strip()
        if not text:
            return

        now = asyncio.get_event_loop().time()
        last_sent = last_partial_sent_at.get(item_id, 0.0)
        if now - last_sent < 0.15:
            return
        last_partial_sent_at[item_id] = now

        entry = pending_transcripts.get(item_id)
        if entry is None:
            entry = TranscriptEntry(
                id=f"rt_{item_id}",
                timestamp=datetime.utcnow().isoformat(),
                speaker="Unknown",
                text=text,
                confidence=0.0,
                latency_ms=0.0,
            )
            pending_transcripts[item_id] = entry
            state.transcript.append(entry)
            try:
                await manager.send_message(
                    meeting_id, {"type": "transcript", "data": entry.__dict__}
                )
            except Exception as e:
                logger.warning(f"[{meeting_id}] Failed to send partial transcript: {e}")
        else:
            entry.text = text
            try:
                await manager.send_message(
                    meeting_id,
                    {
                        "type": "transcript_update",
                        "data": {"id": entry.id, "text": entry.text},
                    },
                )
            except Exception as e:
                logger.warning(f"[{meeting_id}] Failed to update partial transcript: {e}")

        if pending_speech_end:
            pending_speech_end = False
            await maybe_run_agents()

    async def add_transcript(
        text: str,
        latency_ms: float | None = None,
        speaker_override: str | None = None,
        item_id: str | None = None,
    ):
        start_perf = asyncio.get_event_loop().time()
        logger.info(f"=== TRANSCRIPT RECEIVED: '{text}' ===")

        speaker = speaker_override or "Unknown"
        entry = None
        if item_id:
            entry = pending_transcripts.pop(item_id, None)
        if entry is None:
            entry = TranscriptEntry(
                id=f"tr_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.utcnow().isoformat(),
                speaker=speaker,
                text=text,
                confidence=0.0 if speaker == "Unknown" else 1.0,
                latency_ms=(latency_ms or 0.0)
                + max(0.0, (asyncio.get_event_loop().time() - start_perf) * 1000),
            )
            state.transcript.append(entry)
            logger.info(f"Sending transcript to frontend for meeting: {meeting_id}")
            try:
                await manager.send_message(
                    meeting_id, {"type": "transcript", "data": entry.__dict__}
                )
                logger.info("Transcript sent successfully")
            except Exception as e:
                logger.error(f"Failed to send transcript: {e}")
        else:
            entry.text = text
            entry.latency_ms = (latency_ms or 0.0) + max(
                0.0, (asyncio.get_event_loop().time() - start_perf) * 1000
            )
            entry.confidence = 0.0 if speaker == "Unknown" else 1.0
            try:
                await manager.send_message(
                    meeting_id,
                    {
                        "type": "transcript_update",
                        "data": {
                            "id": entry.id,
                            "text": entry.text,
                            "latencyMs": entry.latency_ms,
                        },
                    },
                )
            except Exception as e:
                logger.warning(f"[{meeting_id}] Failed to send transcript update: {e}")

        asyncio.create_task(storage.append_transcript_entry(state, entry))

        if speaker_override:
            if _apply_speaker_stats(entry, speaker_override):
                await _send_speaker_stats()
        else:
            asyncio.create_task(_enrich_transcript(entry))
            await maybe_run_agents()

    async def run_agents():
        # 멀티에이전트 병렬 분석 (SafetyOrchestrator)
        result = await safety_orchestrator.analyze(state, state.transcript[-10:])
        intervention = result.intervention
        if result.errors:
            logger.warning(f"[{meeting_id}] Agent errors: {[e.error for e in result.errors]}")
        if result.warnings:
            logger.warning(f"[{meeting_id}] Safety warnings: {result.warnings}")

        if intervention:
            state.interventions.append(intervention)
            if intervention.parking_lot_item:
                state.parking_lot.append(intervention.parking_lot_item)

            try:
                await manager.send_message(
                    meeting_id,
                    {
                        "type": "intervention",
                        "data": {
                            "id": intervention.id,
                            "type": intervention.intervention_type.value,
                            "message": intervention.message,
                            "timestamp": intervention.timestamp,
                            "violatedPrinciple": intervention.violated_principle,
                            "parkingLotItem": intervention.parking_lot_item,
                        },
                    },
                )
            except Exception as e:
                logger.warning(f"[{meeting_id}] Failed to send intervention: {e}")

    async def on_transcript(text: str, latency_ms: float | None = None, item_id: str | None = None):
        await add_transcript(text, latency_ms=latency_ms, item_id=item_id)

    async def on_speech_end():
        nonlocal pending_speech_end
        pending_speech_end = True

    async def on_partial_transcript(item_id: str, text: str):
        await add_partial_transcript(item_id, text)

    async def on_stt_error(error: Exception):
        error_text = str(error) or error.__class__.__name__
        logger.error(f"STT service error: {error_text}")
        await manager.send_message(
            meeting_id,
            {
                "type": "error",
                "data": {
                    "code": "STT_ERROR",
                    "message": error_text,
                    "recoverable": True,
                },
            },
        )

    def on_connection_state_change(old_state: ConnectionState, new_state: ConnectionState):
        logger.info(f"STT connection state: {old_state.value} -> {new_state.value}")
        if new_state == ConnectionState.RECONNECTING:
            asyncio.create_task(manager.send_message(
                meeting_id,
                {"type": "stt_status", "data": {"status": "reconnecting"}},
            ))
        elif new_state == ConnectionState.CONNECTED:
            asyncio.create_task(manager.send_message(
                meeting_id,
                {"type": "stt_status", "data": {"status": "connected"}},
            ))
        elif new_state == ConnectionState.FAILED:
            asyncio.create_task(manager.send_message(
                meeting_id,
                {"type": "stt_status", "data": {"status": "failed"}},
            ))

    async def run_agent_mode():
        nonlocal agent_mode_enabled
        loop = asyncio.get_running_loop()
        logger.info(f"[{meeting_id}] Agent mode started")
        while agent_mode_enabled:
            if not state.participants:
                await asyncio.sleep(1.0)
                continue

            for _ in range(len(state.participants)):
                prefix_written = False
                ts = datetime.utcnow().isoformat()
                turn_offset = _

                def stream_callback(speaker_name: str, chunk: str):
                    nonlocal prefix_written, ts
                    if not agent_mode_enabled:
                        return
                    if not prefix_written:
                        storage.append_transcription_stream(
                            state.meeting_id, f"\n[{ts}] {speaker_name}: "
                        )
                        prefix_written = True
                    storage.append_transcription_stream(state.meeting_id, chunk)
                    asyncio.run_coroutine_threadsafe(
                        manager.send_message(
                            meeting_id,
                            {
                                "type": "transcript_stream",
                                "data": {
                                    "timestamp": ts,
                                    "speaker": speaker_name,
                                    "chunk": chunk,
                                },
                            },
                        ),
                        loop,
                    )

                try:
                    utterances = await asyncio.to_thread(
                        persona_agent.generate_dialogue,
                        state,
                        state.transcript[-12:],
                        1,
                        None,
                        turn_offset,
                        True,
                        stream_callback,
                    )
                except asyncio.CancelledError:
                    agent_mode_enabled = False
                    break
                except Exception as e:
                    logger.error(f"[{meeting_id}] Agent mode generation failed: {e}", exc_info=True)
                    await manager.send_message(
                        meeting_id,
                        {
                            "type": "error",
                            "data": {
                                "code": "AGENT_MODE_FAILURE",
                                "message": pick(
                                    "에이전트 모드 대화 생성에 실패했습니다. 환경 설정을 확인해주세요.",
                                    "Failed to generate agent-mode dialogue. Please check your environment configuration.",
                                ),
                                "recoverable": False,
                            },
                        },
                    )
                    agent_mode_enabled = False
                    break

                if not agent_mode_enabled:
                    break

                if not utterances:
                    await asyncio.sleep(0.5)
                    continue

                utt = utterances[0]
                if prefix_written and agent_mode_enabled:
                    storage.append_transcription_stream(state.meeting_id, "\n")

                entry = TranscriptEntry(
                    id=f"agent_{uuid.uuid4().hex[:8]}",
                    timestamp=ts,
                    speaker=utt.speaker,
                    text=utt.text,
                    confidence=1.0,
                    latency_ms=0.0,
                )
                for p in state.participants:
                    if p.name == entry.speaker:
                        p.speaking_count += 1
                        break

                state.transcript.append(entry)
                await storage.append_transcript_entry(state, entry)
                try:
                    await manager.send_message(
                        meeting_id,
                        {"type": "transcript", "data": entry.__dict__}
                    )
                except Exception as e:
                    logger.error(f"[{meeting_id}] Failed to send agent transcript: {e}")

                await _send_speaker_stats()

                # Run new agent orchestration pipeline
                # Triage → Judge Agents → Intervention Agent
                try:
                    intervention = await agent_orchestrator.process_transcript(meeting_context)
                    if intervention:
                        logger.info(f"[{meeting_id}] Agent intervention triggered: {intervention.intervention_type.value}")
                except Exception as e:
                    logger.error(f"[{meeting_id}] Agent orchestration failed: {e}", exc_info=True)

                await asyncio.sleep(0.8)

            await asyncio.sleep(1.0)

        logger.info(f"[{meeting_id}] Agent mode stopped")

    stt_connected = False
    if stt_enabled:
        try:
            await stt_service.connect(
                on_transcript,
                on_speech_end,
                on_error=on_stt_error,
                on_connection_state_change=on_connection_state_change,
                on_partial_transcript=on_partial_transcript,
            )
            stt_connected = True
            logger.info(f"Realtime STT connected for meeting {meeting_id}")
        except STTConfigurationError as e:
            logger.error(f"STT configuration error: {e}")
            await manager.send_message(
                meeting_id,
                {
                    "type": "error",
                    "data": {
                        "code": "STT_CONFIGURATION_ERROR",
                        "message": "Speech-to-text service is not properly configured",
                        "recoverable": False,
                    },
                },
            )
        except STTConnectionError as e:
            logger.error(f"STT connection error: {e}")
            await manager.send_message(
                meeting_id,
                {
                    "type": "error",
                    "data": {
                        "code": "STT_CONNECTION_ERROR",
                        "message": "Failed to connect to speech-to-text service",
                        "recoverable": True,
                    },
                },
            )
        except Exception as e:
            logger.error(f"Unexpected STT error: {e}", exc_info=True)
    else:
        logger.info(f"[{meeting_id}] STT disabled for agent meeting; skipping connection")

    audio_chunk_count = 0
    logger.info(f"[{meeting_id}] Entering receive loop, waiting for audio...")
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect as e:
                logger.info(
                    f"WebSocket receive loop ended for meeting {meeting_id} (code={getattr(e, 'code', 'unknown')})"
                )
                break
            message_type = data.get("type")
            if message_type == "agent_mode":
                action = data.get("action")
                payload = data.get("data") or {}

                participants_payload = payload.get("participants") or []
                if isinstance(participants_payload, list) and participants_payload:
                    updated = _coerce_participants(participants_payload, state.participants)
                    if updated:
                        state.participants = updated
                        speaker_service.set_participants(state.participants)

                agenda_payload = payload.get("agenda")
                if isinstance(agenda_payload, str) and agenda_payload:
                    state.agenda = agenda_payload

                title_payload = payload.get("title")
                if isinstance(title_payload, str) and title_payload:
                    state.title = title_payload

                if action == "start":
                    if not persona_agent.client or not persona_agent.model:
                        await manager.send_message(
                            meeting_id,
                            {
                                "type": "error",
                                "data": {
                                    "code": "AGENT_MODE_UNAVAILABLE",
                                    "message": pick(
                                        "OPENAI_API_KEY가 설정되어 있지 않아 에이전트 모드를 사용할 수 없습니다.",
                                        "Agent mode is unavailable because OPENAI_API_KEY is not set.",
                                    ),
                                    "recoverable": False,
                                },
                            },
                        )
                        continue

                    if agent_mode_task and not agent_mode_task.done():
                        await manager.send_message(
                            meeting_id,
                            {"type": "agent_mode_status", "data": {"status": "already_running"}},
                        )
                        continue

                    agent_mode_enabled = True
                    agent_mode_task = asyncio.create_task(run_agent_mode())
                    await manager.send_message(
                        meeting_id,
                        {"type": "agent_mode_status", "data": {"status": "started"}},
                    )
                elif action == "stop":
                    agent_mode_enabled = False
                    if agent_mode_task and not agent_mode_task.done():
                        agent_mode_task.cancel()
                        try:
                            await agent_mode_task
                        except asyncio.CancelledError:
                            pass
                    await manager.send_message(
                        meeting_id,
                        {"type": "agent_mode_status", "data": {"status": "stopped"}},
                    )
                continue
            if message_type == "participants":
                raw_participants = data.get("data", [])
                if isinstance(raw_participants, list) and raw_participants:
                    updated = _coerce_participants(raw_participants, state.participants)
                    if updated:
                        state.participants = updated
                        speaker_service.set_participants(state.participants)
                        logger.info(
                            f"[{meeting_id}] Participants synced: "
                            f"{', '.join(p.name for p in state.participants)}"
                        )
                continue

            if message_type == "audio":
                if not stt_enabled:
                    logger.warning(f"[{meeting_id}] Audio received but STT disabled; dropping chunk")
                    continue
                audio_chunk_count += 1
                audio_size = len(data.get("data", ""))
                logger.info(f"[{meeting_id}] Audio chunk #{audio_chunk_count} received, size: {audio_size} bytes")

                asyncio.create_task(storage.append_audio_chunk(meeting_id, data.get("data", "")))
                if stt_connected and stt_service.is_connected:
                    success = await stt_service.send_audio(data["data"])
                    if success:
                        logger.debug(f"[{meeting_id}] Audio chunk #{audio_chunk_count} sent to OpenAI")
                    else:
                        logger.warning(f"[{meeting_id}] Failed to send audio chunk #{audio_chunk_count}")
                else:
                    logger.warning(f"[{meeting_id}] STT not connected, audio chunk dropped")
    except WebSocketDisconnect as e:
        logger.info(f"WebSocket disconnected for meeting {meeting_id} (code={getattr(e, 'code', 'unknown')})")
        agent_mode_enabled = False
        if agent_mode_task and not agent_mode_task.done():
            agent_mode_task.cancel()
            try:
                await agent_mode_task
            except asyncio.CancelledError:
                pass
        manager.disconnect(meeting_id)
        if stt_enabled:
            await stt_service.disconnect()
        await storage.save_transcript(state)
        await storage.save_interventions(state)
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
        agent_mode_enabled = False
        if agent_mode_task and not agent_mode_task.done():
            agent_mode_task.cancel()
            try:
                await agent_mode_task
            except asyncio.CancelledError:
                pass
        manager.disconnect(meeting_id)
        if stt_enabled:
            await stt_service.disconnect()
        await storage.save_transcript(state)
        await storage.save_interventions(state)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
