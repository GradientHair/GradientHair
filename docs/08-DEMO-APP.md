# Meeting Operator Demo App

This demo app turns the PRD + demo scenario into a runnable prototype. It uses:
- **Python + OpenAI SDK** for recap generation (optional if no key)
- **React (Vite)** for the operator UI
- **Docker Compose** for one-command startup

## What this demo covers

Mapped to the docs you provided:
- **Meeting setup** (title, agenda, participants) → `docs/03-USER-FLOW.md`
- **Ice breaker attendance check** + **attendee correction** → `docs/05-DEMO-SCENARIO.md`
- **Topic drift + principle violation + participation imbalance** interventions → `docs/04-API-SPEC.md`
- **Meeting recap + action items + saved markdown files** → `docs/02-ARCHITECTURE.md`

This is the **“first version”**: it simulates an online meeting stream with test text. The next step is to swap the transcript source to live audio + Realtime API.

---

## Repo layout (new)

```
backend/        # FastAPI app
  app/
    main.py     # Demo API
    demo/       # Demo script(s)
frontend/       # React (Vite)
docker-compose.yml
meetings/       # Saved markdown files (runtime)
```

## Customizing the demo script

Edit `backend/app/demo/demo_script.json` to add new scripts or tweak events:
- `participants`: attendee list used by the ice breaker
- `steps`: transcript lines + tags like `TOPIC_DRIFT` or `PRINCIPLE_VIOLATION`
- `action_items`: pre-seeded action items for the recap

---

## How to run (Docker)

1) Set your API key (optional but recommended for AI recap):

```bash
export OPENAI_API_KEY=sk-...
```

2) Start services:

```bash
docker compose up --build
```

3) Open the UI:

```
http://localhost:3000
```

---

## How to run (local dev)

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## How to test (demo scenario)

1) **Open UI** at `http://localhost:3000`.
2) Click **Apply demo defaults** (pre-fills title, agenda, attendees).
3) Click **Start meeting demo**.
4) Verify the following sequence:
   - Ice breaker appears and lists expected attendees.
   - Someone mentions a wrong attendee → moderator correction appears.
   - Topic drift intervention appears.
   - Principle violation intervention appears.
   - Participation check prompts a quiet attendee.
   - Recap appears with summary + action items.
5) Confirm markdown files were written to `meetings/<date>-<title>/`:
   - `preparation.md`
   - `transcript.md`
   - `interventions.md`
   - `summary.md`
   - `action-items.md`

### API quick check (optional)
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/demo/scripts
```

---

## Next step for live streaming

Replace the demo transcript timeline with:
- Browser audio capture (WebRTC / Web Audio API)
- OpenAI Realtime API transcription
- Real-time events emitted to the frontend

All UI and storage layers already match the expected contract, so you can swap the data source without breaking the demo flow.
