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
    STTError,
    STTConnectionError,
    STTConfigurationError,
    ConnectionState,
)
from services.speaker_service import SpeakerService
from services.storage_service import StorageService
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
    meeting_id = f"{datetime.now().strftime('%Y-%m-%d')}-{request.title.lower().replace(' ', '-')}"

    participants = [
        Participant(id=p.get("id", str(uuid.uuid4())), name=p["name"], role=p["role"])
        for p in request.participants
    ]

    # 원칙 로드 (간단히 하드코딩)
    principles = []
    if "agile" in request.principleIds:
        principles.append({"id": "agile", "name": "수평적 의사결정"})
        principles.append({"id": "agile", "name": "타임박스"})
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
    try:
        review_agent = ReviewOrchestratorAgent()
        review = await review_agent.review(state)
        await storage.save_summary(state, review.summary_markdown)
        await storage.save_action_items(state, review.action_items_markdown)
        await storage.save_individual_feedback(state, review.feedback_by_participant)
    except Exception as e:
        logger.error(f"Review generation failed: {e}")

    return {"id": meeting_id, "status": "completed"}


@app.post("/api/v1/meetings/{meeting_id}/save")
async def save_meeting(meeting_id: str, request: SaveMeetingRequest):
    """데모 모드에서 프론트엔드 데이터를 저장"""
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
    try:
        review_agent = ReviewOrchestratorAgent()
        review = await review_agent.review(state)
        await storage.save_summary(state, review.summary_markdown)
        await storage.save_action_items(state, review.action_items_markdown)
        await storage.save_individual_feedback(state, review.feedback_by_participant)
    except Exception as e:
        logger.error(f"Review generation failed: {e}")

    return {"id": meeting_id, "status": "saved", "files": [
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
            await self.active_connections[meeting_id].send_json(message)


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

    async def on_transcript(text: str):
        logger.info(f"=== TRANSCRIPT RECEIVED: '{text}' ===")

        # 화자 식별 (간소화 - 첫 번째 참석자로 기본 설정)
        if state.participants:
            speaker = state.participants[0].name
        else:
            speaker = "Unknown"

        logger.info(f"Speaker: {speaker}")

        # 참석자 통계 업데이트
        for p in state.participants:
            if p.name == speaker:
                p.speaking_count += 1
                break

        entry = TranscriptEntry(
            id=f"tr_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow().isoformat(),
            speaker=speaker,
            text=text,
            confidence=1.0,  # Default confidence since speaker identification is simplified
        )
        state.transcript.append(entry)

        logger.info(f"Sending transcript to frontend for meeting: {meeting_id}")
        try:
            await manager.send_message(
                meeting_id, {"type": "transcript", "data": entry.__dict__}
            )
            logger.info(f"Transcript sent successfully")
        except Exception as e:
            logger.error(f"Failed to send transcript: {e}")

        # 발언 통계 전송
        total = sum(p.speaking_count for p in state.participants)
        if total > 0:
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

    async def on_speech_end():
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

    # Error callback for STT service
    async def on_stt_error(error: Exception):
        logger.error(f"STT service error: {error}")
        # Notify client about STT error but don't crash the meeting
        await manager.send_message(
            meeting_id,
            {
                "type": "error",
                "data": {
                    "code": "STT_ERROR",
                    "message": str(error),
                    "recoverable": True,
                },
            },
        )

    # Connection state change callback
    def on_connection_state_change(old_state: ConnectionState, new_state: ConnectionState):
        logger.info(f"STT connection state: {old_state.value} -> {new_state.value}")
        if new_state == ConnectionState.RECONNECTING:
            asyncio.create_task(manager.send_message(
                meeting_id,
                {
                    "type": "stt_status",
                    "data": {"status": "reconnecting"},
                },
            ))
        elif new_state == ConnectionState.CONNECTED:
            asyncio.create_task(manager.send_message(
                meeting_id,
                {
                    "type": "stt_status",
                    "data": {"status": "connected"},
                },
            ))
        elif new_state == ConnectionState.FAILED:
            asyncio.create_task(manager.send_message(
                meeting_id,
                {
                    "type": "stt_status",
                    "data": {"status": "failed"},
                },
            ))

    stt_connected = False
    try:
        await stt_service.connect(
            on_transcript,
            on_speech_end,
            on_error=on_stt_error,
            on_connection_state_change=on_connection_state_change,
        )
        stt_connected = True
        logger.info(f"STT service connected for meeting {meeting_id}")
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
        # STT service connection failed, but WebSocket connection remains open

    audio_chunk_count = 0
    logger.info(f"[{meeting_id}] Entering receive loop, waiting for audio...")
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "audio":
                audio_chunk_count += 1
                audio_size = len(data.get("data", ""))
                logger.info(f"[{meeting_id}] Audio chunk #{audio_chunk_count} received, size: {audio_size} bytes")

                if stt_connected and stt_service.is_connected:
                    success = await stt_service.send_audio(data["data"])
                    if success:
                        logger.debug(f"[{meeting_id}] Audio chunk #{audio_chunk_count} sent to OpenAI")
                    else:
                        logger.warning(f"[{meeting_id}] Failed to send audio chunk #{audio_chunk_count}")
                else:
                    logger.warning(f"[{meeting_id}] STT not connected, audio chunk dropped")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for meeting {meeting_id}")
        manager.disconnect(meeting_id)
        await stt_service.disconnect()
        await storage.save_transcript(state)
        await storage.save_interventions(state)
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
        manager.disconnect(meeting_id)
        await stt_service.disconnect()
        await storage.save_transcript(state)
        await storage.save_interventions(state)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
