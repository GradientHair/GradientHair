from __future__ import annotations

from datetime import datetime
from typing import Dict

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models import DemoStartRequest, DemoStartResponse, MeetingCreate, MeetingRecord
from app.services.demo_engine import DemoEngine
from app.services.script_loader import get_script, summarize_scripts
from app.services.text_utils import slugify

app = FastAPI(title="Meeting Operator Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEETINGS: Dict[str, MeetingRecord] = {}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/demo/scripts")
async def list_demo_scripts() -> dict:
    scripts = summarize_scripts(settings.demo_script_path)
    return {"scripts": [script.model_dump() for script in scripts]}


@app.get("/api/demo/scripts/{script_id}")
async def get_demo_script(script_id: str) -> dict:
    script = get_script(settings.demo_script_path, script_id)
    return {"script": script.model_dump()}


@app.post("/api/meetings", response_model=MeetingRecord)
async def create_meeting(payload: MeetingCreate) -> MeetingRecord:
    meeting_id = f"{datetime.now().strftime('%Y-%m-%d')}-{slugify(payload.title)}"
    record = MeetingRecord(
        id=meeting_id,
        title=payload.title,
        agenda=payload.agenda,
        participants=payload.participants,
        status="preparing",
        created_at=datetime.utcnow().isoformat(),
    )
    MEETINGS[meeting_id] = record
    return record


@app.post("/api/meetings/{meeting_id}/start", response_model=DemoStartResponse)
async def start_meeting(
    meeting_id: str,
    payload: DemoStartRequest | None = Body(default=None),
) -> DemoStartResponse:
    record = MEETINGS.get(meeting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")

    record.status = "in_progress"
    record.started_at = datetime.utcnow().isoformat()

    script_id = payload.demo_script_id if payload and payload.demo_script_id else None
    script = get_script(settings.demo_script_path, script_id)
    engine = DemoEngine(record, script)
    timeline = await engine.build()

    record.status = "completed"
    record.ended_at = datetime.utcnow().isoformat()

    return DemoStartResponse(meeting=record, events=timeline.events)
