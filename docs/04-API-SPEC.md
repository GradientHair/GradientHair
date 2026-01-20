# MeetingMod - API Specification

## 1. API 개요

### 아키텍처 결정
- **Backend**: Python 3.12 + OpenAI Agents SDK
- **Web Server**: FastAPI (필요 시)
- **Storage**: 로컬 파일시스템 (Markdown 파일)
- **실시간 통신**: WebSocket

### Base URL
```
Development: http://localhost:8000/api/v1
```

### Authentication
해커톤에서는 인증 생략 (MVP)

---

## 2. 파일 저장 구조

### 2.1 디렉토리 구조
```
meetingmod/
├── meetings/                          # 회의 데이터
│   └── {YYYY-MM-DD-meeting-title}/   # 회의별 디렉토리
│       ├── preparation.md            # 회의 준비 자료
│       ├── principles.md             # 적용된 회의 원칙
│       ├── transcript.md             # 실시간 녹취록
│       ├── interventions.md          # Agent 개입 기록
│       ├── summary.md                # 회의 요약
│       └── action-items.md           # Action Items
│
└── principles/                        # 회의 원칙 템플릿
    ├── agile.md
    └── aws-leadership.md
```

### 2.2 파일 포맷

#### preparation.md
```markdown
# 회의 준비 자료

## 회의 정보
- **제목**: 주간 제품팀 스프린트 리뷰
- **일시**: 2026-01-20 14:00
- **상태**: preparing | in_progress | completed

## 참석자
| 이름 | 역할 |
|------|------|
| 김철수 | PM |
| 이민수 | Frontend |
| 박영희 | Backend |
| 최지은 | Design |

## 아젠다
1. 지난 스프린트 회고
   - 완료된 태스크 리뷰
   - 발생한 이슈 논의
2. 다음 스프린트 계획
   - 우선순위 선정
   - 리소스 배분

## 참고 자료
- [스프린트 보드](https://notion.so/sprint)
```

#### transcript.md
```markdown
# 회의 녹취록

회의: 주간 제품팀 스프린트 리뷰
일시: 2026-01-20 14:00 - 14:45

---

[14:00:12] **김철수**: 지난 스프린트에서 8개 태스크를 완료했습니다.

[14:00:30] **이민수**: 네, 성과가 좋았어요.

[14:00:45] **이민수**: 그런데 점심 뭐 먹을까요?

---
> 🤖 **[INTERVENTION - TOPIC_DRIFT]** 14:00:48
> "현재 주제로 돌아갈까요? '점심 메뉴'는 Parking Lot에 추가했습니다."
---

[14:01:10] **김철수**: 아, 네. 다음 스프린트 계획을 보면...
```

#### interventions.md
```markdown
# Agent 개입 기록

회의: 주간 제품팀 스프린트 리뷰

---

## 개입 #1
- **시간**: 14:00:48
- **유형**: TOPIC_DRIFT
- **트리거**: "점심 뭐 먹을까요?"
- **메시지**: "현재 주제로 돌아갈까요? '점심 메뉴'는 Parking Lot에 추가했습니다."
- **Parking Lot**: 점심 메뉴

## 개입 #2
- **시간**: 14:15:30
- **유형**: PARTICIPATION_IMBALANCE
- **트리거**: 박영희 발언 비율 8%
- **메시지**: "박영희 님, 백엔드 관점에서 의견이 있으실까요?"
```

#### action-items.md
```markdown
# Action Items

회의: 주간 제품팀 스프린트 리뷰
생성일: 2026-01-20

---

## 할당된 업무

1. **A/B 테스트 설계안 작성**
   - 담당: 김철수
   - 기한: 2026-01-22
   - 맥락: 스프린트 계획 논의 중 결정

2. **API 성능 테스트 완료**
   - 담당: 박영희
   - 기한: 2026-01-24
   - 맥락: 백엔드 최적화 논의

3. **디자인 시안 검토**
   - 담당: 최지은
   - 기한: 2026-01-23
   - 맥락: 온보딩 개선 논의
```

---

## 3. REST API Endpoints

### 3.1 Principles Management

#### Get All Principles
```http
GET /principles

Response: 200 OK
{
  "principles": [
    {
      "id": "agile",
      "name": "Agile 원칙",
      "filePath": "principles/agile.md",
      "content": "# Agile Meeting Principles\n\n1. **수평적 의사결정**..."
    },
    {
      "id": "aws-leadership",
      "name": "AWS Leadership Principles",
      "filePath": "principles/aws-leadership.md",
      "content": "..."
    }
  ]
}
```

#### Get Single Principle
```http
GET /principles/{principle_id}

Response: 200 OK
{
  "id": "agile",
  "name": "Agile 원칙",
  "content": "# Agile Meeting Principles\n\n1. **수평적 의사결정**..."
}
```

#### Update Principle
```http
PUT /principles/{principle_id}

Request:
{
  "name": "Agile 원칙",
  "content": "# Agile Meeting Principles\n\n1. **수평적 의사결정**..."
}

Response: 200 OK
```

#### Create Custom Principle
```http
POST /principles

Request:
{
  "name": "우리팀 원칙",
  "content": "# 우리팀 회의 원칙\n\n1. ..."
}

Response: 201 Created
{
  "id": "custom-001",
  "name": "우리팀 원칙",
  "filePath": "principles/custom-001.md"
}
```

### 3.2 Meeting Management

#### Create Meeting
```http
POST /meetings

Request:
{
  "title": "주간 제품팀 스프린트 리뷰",
  "agenda": "## 오늘의 아젠다\n1. 지난 스프린트 회고\n2. 다음 스프린트 계획",
  "participants": [
    {"name": "김철수", "role": "PM"},
    {"name": "이민수", "role": "Frontend"},
    {"name": "박영희", "role": "Backend"},
    {"name": "최지은", "role": "Design"}
  ],
  "principleIds": ["agile", "aws-leadership"],
  "referenceLinks": [
    "https://notion.so/sprint-board"
  ]
}

Response: 201 Created
{
  "id": "2026-01-20-sprint-review",
  "title": "주간 제품팀 스프린트 리뷰",
  "status": "preparing",
  "directory": "meetings/2026-01-20-sprint-review/",
  "createdAt": "2026-01-20T14:00:00Z"
}
```

#### Get Meeting
```http
GET /meetings/{meeting_id}

Response: 200 OK
{
  "id": "2026-01-20-sprint-review",
  "title": "주간 제품팀 스프린트 리뷰",
  "status": "in_progress",
  "directory": "meetings/2026-01-20-sprint-review/",
  "participants": [...],
  "principles": [...],
  "startedAt": "2026-01-20T14:00:00Z",
  "speakerStats": {
    "김철수": {"percentage": 45, "speakingTime": 540, "count": 12},
    "이민수": {"percentage": 30, "speakingTime": 360, "count": 8},
    "박영희": {"percentage": 15, "speakingTime": 180, "count": 4},
    "최지은": {"percentage": 10, "speakingTime": 120, "count": 3}
  }
}
```

#### Start Meeting
```http
POST /meetings/{meeting_id}/start

Response: 200 OK
{
  "id": "2026-01-20-sprint-review",
  "status": "in_progress",
  "startedAt": "2026-01-20T14:00:00Z"
}
```

#### End Meeting
```http
POST /meetings/{meeting_id}/end

Response: 200 OK
{
  "id": "2026-01-20-sprint-review",
  "status": "completed",
  "endedAt": "2026-01-20T14:45:00Z",
  "savedFiles": [
    "meetings/2026-01-20-sprint-review/summary.md",
    "meetings/2026-01-20-sprint-review/action-items.md",
    "meetings/2026-01-20-sprint-review/transcript.md",
    "meetings/2026-01-20-sprint-review/interventions.md"
  ]
}
```

---

## 4. WebSocket API

### 4.1 Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/meetings/{meeting_id}');
```

### 4.2 Client → Server Messages

#### Audio Stream
```json
{
  "type": "audio",
  "data": "<base64_encoded_audio_chunk>",
  "timestamp": 1705755600000
}
```

#### Intervention Acknowledgment
```json
{
  "type": "intervention_ack",
  "interventionId": "int_001",
  "action": "acknowledged"
}
```

#### Manual Topic Change
```json
{
  "type": "topic_change",
  "topicIndex": 2,
  "topicTitle": "다음 스프린트 계획"
}
```

### 4.3 Server → Client Messages

#### Transcript Update (화자 자동 분리 포함)
```json
{
  "type": "transcript",
  "data": {
    "id": "tr_001",
    "speaker": "김철수",
    "speakerConfidence": 0.85,
    "text": "그래서 저는 이 기능을 다음 스프린트에서 진행하는 게 맞다고 생각합니다.",
    "timestamp": "2026-01-20T14:23:12Z",
    "isFinal": true
  }
}
```

#### Intervention Alert (경고음 + Toast)
```json
{
  "type": "intervention",
  "data": {
    "id": "int_001",
    "interventionType": "TOPIC_DRIFT",
    "message": "재미있는 이야기네요! 다만 시간 관계상, 현재 논의 중인 '다음 스프린트 우선순위'를 먼저 마무리하면 어떨까요?",
    "triggerContext": "점심 뭐 먹을까요?",
    "violatedPrinciple": null,
    "parkingLotItem": "점심 메뉴 결정",
    "playAlertSound": true,
    "timestamp": "2026-01-20T14:23:35Z"
  }
}
```

#### Principle Violation Alert
```json
{
  "type": "intervention",
  "data": {
    "id": "int_002",
    "interventionType": "PRINCIPLE_VIOLATION",
    "message": "잠깐요! Agile 원칙의 '수평적 의사결정'에 따르면, 중요한 결정은 팀원들과 함께 논의하는 게 좋아요. 다른 분들 의견은 어떠신가요?",
    "triggerContext": "이건 제가 결정했으니까, 다들 이대로 진행해 주세요.",
    "violatedPrinciple": "수평적 의사결정",
    "playAlertSound": true,
    "timestamp": "2026-01-20T14:30:15Z"
  }
}
```

#### Speaker Stats Update
```json
{
  "type": "speaker_stats",
  "data": {
    "stats": {
      "김철수": {"percentage": 45, "speakingTime": 540, "count": 12},
      "이민수": {"percentage": 30, "speakingTime": 360, "count": 8},
      "박영희": {"percentage": 15, "speakingTime": 180, "count": 4},
      "최지은": {"percentage": 10, "speakingTime": 120, "count": 3}
    },
    "imbalanceWarning": {
      "hasWarning": true,
      "lowParticipants": ["박영희", "최지은"]
    }
  }
}
```

#### Meeting End (파일 저장 완료)
```json
{
  "type": "meeting_end",
  "data": {
    "summary": "오늘 회의에서는 지난 스프린트 회고와 다음 스프린트 계획을 논의했습니다...",
    "actionItems": [
      {
        "description": "A/B 테스트 설계안 작성",
        "assignee": "김철수",
        "dueDate": "2026-01-22"
      }
    ],
    "savedFiles": {
      "directory": "meetings/2026-01-20-sprint-review/",
      "files": [
        "preparation.md",
        "transcript.md",
        "interventions.md",
        "summary.md",
        "action-items.md"
      ]
    },
    "qualityReport": {
      "participationBalance": 72,
      "topicFocus": 87,
      "interventionCount": 2,
      "totalDuration": 2700
    }
  }
}
```

---

## 5. Intervention Types

| Type | Code | Trigger Condition | Example Response |
|------|------|-------------------|------------------|
| 주제 이탈 | `TOPIC_DRIFT` | 아젠다와 무관한 주제 감지 (LLM 판단) | "현재 주제로 돌아갈까요?" |
| 원칙 위반 | `PRINCIPLE_VIOLATION` | 설정된 원칙과 충돌 (LLM 판단) | "Agile 원칙의 '수평적 의사결정'에 따르면..." |
| 참여 불균형 | `PARTICIPATION_IMBALANCE` | 특정 참석자 발언 비율 15% 미만 (10분 경과 후) | "박영희 님 의견도 들어볼까요?" |
| Top-down 감지 | `TOP_DOWN_DECISION` | 합의 없이 일방적 결정 발언 감지 | "다른 분들 의견은 어떠신가요?" |

### 개입 타이밍
- **트리거**: 발화자가 말을 멈췄을 때 (침묵 1-2초 감지)
- **출력**: 경고음 재생 + Toast 메시지 표시
- **빈도 제한**: 연속 개입 사이 최소 2분 간격

---

## 6. OpenAI API Integration

### 6.1 Realtime API (실시간 STT)
```python
import asyncio
import websockets
import json

# OpenAI Realtime API WebSocket 연결
REALTIME_API_URL = "wss://api.openai.com/v1/realtime"

async def connect_realtime_api(api_key: str, on_transcript: callable):
    """
    OpenAI Realtime API를 통한 실시간 음성 인식
    - WebSocket 기반 저지연 STT
    - 스트리밍 응답으로 즉각적인 자막 표시
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1"
    }

    async with websockets.connect(REALTIME_API_URL, extra_headers=headers) as ws:
        # 세션 설정
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "silence_duration_ms": 1500  # 1.5초 침묵 감지
                }
            }
        }))

        # 메시지 수신 루프
        async for message in ws:
            data = json.loads(message)
            if data["type"] == "conversation.item.input_audio_transcription.completed":
                transcript = data["transcript"]
                await on_transcript(transcript)

async def send_audio_chunk(ws, audio_base64: str):
    """오디오 청크 전송"""
    await ws.send(json.dumps({
        "type": "input_audio_buffer.append",
        "audio": audio_base64
    }))
```

### 6.2 GPT-5.2 (Agent Reasoning)
```python
# Moderator Agent - 개입 필요성 판단
system_prompt = """You are a meeting moderator AI.
Current agenda: {agenda}
Meeting principles: {principles}
Participants: {participants}

Analyze the recent conversation and determine if intervention is needed.
BE DIRECT AND COURAGEOUS - intervene actively when needed.

Return JSON:
{
  "needs_intervention": true/false,
  "intervention_type": "TOPIC_DRIFT" | "PRINCIPLE_VIOLATION" | "PARTICIPATION_IMBALANCE" | "TOP_DOWN_DECISION" | null,
  "message": "개입 메시지 (한국어, 직접적이고 용기있는 톤)",
  "violated_principle": "위반된 원칙명" | null,
  "parking_lot_item": "주제 이탈 시 추가할 항목" | null
}
"""

response = client.chat.completions.create(
    model="gpt-5.2",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Recent transcript:\n{recent_transcript}"}
    ],
    response_format={"type": "json_object"}
)
```

### 6.3 화자 분리 (GPT-5.2 활용)
```python
# 참석자 목록 기반 화자 추론 (GPT-5.2의 향상된 컨텍스트 이해력 활용)
speaker_prompt = """Given the participants and their roles:
{participants}

And this speech segment:
"{text}"

Identify who is most likely speaking based on:
1. Speaking style and vocabulary
2. Topic relevance to their role
3. Context from previous utterances
4. Korean honorific patterns and speech register

Return JSON:
{
  "speaker": "이름",
  "confidence": 0.0-1.0
}
"""

response = client.chat.completions.create(
    model="gpt-5.2",
    messages=[{"role": "user", "content": speaker_prompt}],
    response_format={"type": "json_object"}
)
```

---

## 7. Error Codes

| Code | Description |
|------|-------------|
| `MEETING_NOT_FOUND` | 회의를 찾을 수 없음 |
| `PRINCIPLE_NOT_FOUND` | 원칙 템플릿을 찾을 수 없음 |
| `FILE_WRITE_ERROR` | 파일 저장 실패 |
| `STT_ERROR` | 음성 인식 실패 |
| `AGENT_ERROR` | Agent 처리 실패 |
| `WEBSOCKET_ERROR` | WebSocket 연결 오류 |
