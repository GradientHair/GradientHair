# GradientHair

> Multi-agent meeting moderator demo with real-time intervention and post-meeting feedback

English | [한국어](README.md)

## Demo

- Demo URL: (Coming soon)
- Demo Video: (Coming soon)

### Running the Demo (Docker)

```bash
# 1. Create backend/.env and add API key
echo "OPENAI_API_KEY=<YOUR_API_KEY>" > backend/.env

# 2. Run docker compose
docker compose --env-file backend/.env -f docker/docker-compose.yml up -d --build

# 3. Clean up after demo
docker compose --env-file backend/.env -f docker/docker-compose.yml down
```

### Demo Flow

1. Access `http://localhost:3000`
2. Enter meeting title/participants/agenda
3. **Start Meeting** → Navigate to `/meeting/{id}`
4. Check real-time captions/interventions in **Agent Mode**
5. **End Meeting** → Navigate to `/review/{id}` and verify saved files

## Problem Statement

- Employees spend avg. 15 hours/week in meetings, **over 50% rated unproductive**
- **37% of meeting time** wasted on off-topic discussions
- **70% of participants** experience unequal speaking opportunities
- **Over 30% of Action Items** not clearly documented and lost

## Solution

- Collect utterances via Realtime STT and update Meeting State
- Multi-agent performs real-time intervention
- After meeting, Review Agent saves summary/action items/feedback as Markdown
- LLM output validation: Pydantic schema + error feedback retry + optional DSPy verification
- Cost/latency optimization: Model router, deferred diarization post-processing

## Requirements Checklist

- [x] OpenAI API usage
- [x] Multi-agent implementation
- [x] Working demo
- [x] LLM structured output validation pipeline
- [x] Practical cost/latency optimization

## Architecture

### Multi-Agent Patterns

| Pattern | Application |
| ------- | ----------- |
| **Blackboard** | Meeting State Store as shared memory, all Agents read/write state |
| **Moderator + Worker** | Triage Agent classifies intent and delegates to specialist Agents (Topic/Principle/Participation) |
| **Verifier + Executor** | Validate LLM output with Pydantic before execution, retry loop on failure |

### System Structure

```
Meeting (Live):
  Audio -> Realtime STT -> Meeting State Store (Blackboard)
                      |
                      v
               Triage Agent (Moderator - Intent classification / Handoff)
              /       |        \
         Topic    Principle  Participation    (Workers)
         Agent       Agent       Agent
              \       |        /
                Intervention Merge
                       |
                  Alert + Toast

Post-meeting (Async):
  Review Agent -> summary/action-items/feedback.md
  Diarize Job  -> transcript_diarized.md/.json
```

## Tech Stack

- **Backend**: Python 3.12, FastAPI
- **AI/Agents**: OpenAI SDK, OpenAI Agents SDK
- **STT**: OpenAI Realtime API
- **Frontend**: Next.js, React, shadcn/ui

## Installation & Running

```bash
# Set up environment
make env-backend   # Creates backend/.env, then add OPENAI_API_KEY
make env-frontend  # Creates frontend/.env.local

# Install dependencies
make setup-backend
make setup-frontend

# Run
make run-local-dev
```

## Future Plans

- Realtime STT pipeline stabilization and latency optimization
- Model/policy evaluation (Eval) automation

## Team

| Name | Role |
| ---- | ---- |
| Huncheol Shin | Team Lead/Planning, Agent Dev |
| Donghyun Kim | STT Development |
| Jongseob Jeon | App Development |
| Jaeyeon Kim | Agent Development |

## Documentation

- [Developer Guide](docs/DEVELOPER-GUIDE.en.md)
