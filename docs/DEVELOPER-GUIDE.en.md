# Developer Guide

English | [한국어](DEVELOPER-GUIDE.ko.md)

This document covers the technical details of the MeetingMod project.

## Table of Contents

- [Project Structure](#project-structure)
- [Environment Setup](#environment-setup)
- [Backend](#backend)
- [Frontend](#frontend)
- [Multi-Agent System](#multi-agent-system)
- [LLM Output Validation](#llm-output-validation)
- [Data Models](#data-models)
- [Real-time Pipeline](#real-time-pipeline)
- [Related Documents](#related-documents)

## Project Structure

```
GradientHair/
├── frontend/                 # Next.js app
│   ├── app/                  # App Router pages
│   ├── components/           # React components
│   └── lib/                  # Utilities
│
├── backend/                  # Python server
│   ├── server.py             # FastAPI main server
│   ├── agents/               # Multi-Agent implementation
│   ├── services/             # Business logic
│   └── models/               # Data models
│
├── docker/                   # Docker configuration
│   └── docker-compose.yml
│
├── meetings/                 # Meeting data storage
│   └── {meeting-id}/
│       ├── preparation.md
│       ├── transcript.md
│       ├── interventions.md
│       ├── summary.md
│       └── action-items.md
│
├── principles/               # Meeting principle templates
│   ├── agile.md
│   └── aws-leadership.md
│
└── docs/                     # Documentation
```

## Environment Setup

### Requirements

- Node.js 18+
- Python 3.12+
- OpenAI API Key
- Docker (for demo)

### Backend Setup

```bash
# Create environment file
make env-backend

# Edit backend/.env
OPENAI_API_KEY=your_key_here
CORS_ORIGINS=http://localhost:3000
```

### Frontend Setup

```bash
# Create environment file
make env-frontend

# frontend/.env.local (auto-generated)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Running

```bash
# Run with Docker (recommended)
docker compose --env-file backend/.env -f docker/docker-compose.yml up -d --build

# Or local development mode
make run-local-dev

# Run individually
make run-backend   # Backend only
make run-frontend  # Frontend only
```

## Backend

### Tech Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | REST API, WebSocket server |
| OpenAI Realtime API | Real-time speech recognition (STT) |
| OpenAI Agents SDK | Multi-Agent orchestration |
| OpenAI SDK | LLM calls (GPT-4) |

### Key Services

- `server.py` - FastAPI main server (REST + WebSocket)
- `services/` - STT, speaker diarization, storage services
- `agents/` - Multi-Agent implementation

## Frontend

### Tech Stack

| Technology | Purpose |
|------------|---------|
| Next.js | React framework |
| React | UI library |
| Tailwind CSS | Styling |
| shadcn/ui | UI components |
| Zustand | State management |

### Main Pages

- `/` - Meeting preparation page (agenda, participants input)
- `/meeting/{id}` - Meeting in progress page (real-time captions, intervention alerts)
- `/review/{id}` - Meeting results page (summary, Action Items)

## Multi-Agent System

### Agent Structure

```
               Triage Agent (Intent classification / Handoff)
              /       |        \
         Topic    Principle  Participation
         Agent       Agent       Agent
              \       |        /
                Intervention Merge
```

| Agent | Role |
|-------|------|
| Triage Agent | Classify utterance intent, handoff to appropriate Agent |
| Topic Agent | Detect topic drift and guide back |
| Principle Agent | Detect meeting principle violations |
| Participation Agent | Detect participation imbalance and encourage |
| Review Agent | Generate summary, Action Items, feedback after meeting |

### Intervention Types

- `TOPIC_DRIFT` - Guide back when off-topic
- `PRINCIPLE_VIOLATION` - Point out meeting principle violations
- `PARTICIPATION_IMBALANCE` - Encourage participation when imbalanced

## LLM Output Validation

Three-stage LLM output validation:

1. **Pydantic schema parsing** + forced structured output (JSON)
2. **Error feedback retry** - Retry loop with error message on failure
3. **Optional DSPy verification** - Additional safeguard with `DSPY_VALIDATE=1`

Related documentation: [PR #5](https://github.com/GradientHair/GradientHair/pull/5)

### Cost/Latency Optimization

- **Model Router**: Fast model for small tasks, high-performance model for complex tasks
- **Deferred Diarization**: Real-time STT via Realtime API, speaker diarization as batch post-processing

## Data Models

### Meeting

```typescript
interface Meeting {
  id: string;
  title: string;
  status: 'preparing' | 'in_progress' | 'completed';
  agenda: string;
  participants: Participant[];
  principles: Principle[];
  transcript: TranscriptEntry[];
  interventions: Intervention[];
  actionItems: ActionItem[];
}
```

### File Storage Structure

```
meetings/{meeting-id}/
├── preparation.md       # Meeting preparation materials
├── principles.md        # Applied meeting principles
├── transcript.md        # Real-time transcript
├── interventions.md     # Agent intervention records
├── summary.md           # Meeting summary
├── action-items.md      # Action Items
└── transcript_diarized.md  # Speaker-diarized transcript (post-processed)
```

## Real-time Pipeline

```
Audio -> Realtime STT -> Meeting State Store
                    |
                    v
             Triage Agent
            /      |      \
       Topic  Principle  Participation
       Agent     Agent       Agent
            \      |      /
           Intervention Merge
                   |
             Alert + Toast
```

### Processing Cycle

- **STT**: Real-time (streaming)
- **Intervention decision**: Upon utterance end detection
- **Intervention execution**: Immediate (alert sound + Toast)
- **Speaker diarization**: Batch processing after meeting ends

## Related Documents

- [Requirements](00-REQUIREMENTS.md)
- [PRD](01-PRD.md)
- [Architecture](02-ARCHITECTURE.md)
- [User Flow](03-USER-FLOW.md)
- [API Spec](04-API-SPEC.md)
- [Demo Scenario](05-DEMO-SCENARIO.md)
- [Implementation Guide](06-IMPLEMENTATION-GUIDE.md)
- [Multi-Agent Design](07-MULTI-AGENT-DESIGN.md)
