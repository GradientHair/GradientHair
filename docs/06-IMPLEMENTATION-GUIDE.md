# MeetingMod - Implementation Guide for Codex

## 1. 구현 우선순위 (해커톤 7시간 기준)

### Phase 1: 기본 셋업 (1시간)
```
Priority: CRITICAL
목표: 프로젝트 구조 & 기본 UI 셋업
```

1. **프로젝트 초기화**
   - Next.js 14 (App Router) 프로젝트 생성
   - Python 3.12 + OpenAI Agents SDK 백엔드 프로젝트 생성
   - 필수 의존성 설치

2. **기본 UI 컴포넌트**
   - shadcn/ui 설치 및 구성
   - 기본 레이아웃 컴포넌트
   - 회의 준비 화면 기본 구조

### Phase 2: 핵심 기능 - 실시간 파이프라인 (3시간)
```
Priority: CRITICAL
목표: STT → Agent → 개입 파이프라인 완성
```

1. **WebSocket 연결**
   - Frontend ↔ Backend WebSocket 설정
   - 연결 상태 관리

2. **음성 캡처 & STT**
   - 브라우저 마이크 캡처 (Web Audio API)
   - OpenAI Whisper API 연동
   - 실시간 자막 표시
   - AI 자동 화자 분리 (참석자 목록 기반)

3. **Moderator Agent 구현**
   - OpenAI Agents SDK 설정
   - 발화 멈춤 감지 (1-2초 침묵)
   - 주제 이탈 감지 로직
   - 원칙 위반 감지 (LLM 판단)
   - 개입 메시지 생성

4. **개입 UI**
   - 경고음 재생 (시청각 주의 환기)
   - Toast 컴포넌트 표시
   - 개입 타이밍: 발화자가 말을 멈췄을 때

### Phase 3: 부가 기능 (2시간)
```
Priority: HIGH
목표: 데모 완성도 향상
```

1. **회의 원칙 관리 페이지**
   - Agile 원칙 템플릿
   - AWS Leadership Principles 템플릿
   - 커스텀 원칙 추가/수정/삭제
   - 회의별 원칙 선택

2. **발언 통계**
   - AI 자동 화자 분리 (GPT-4o 활용)
   - 발언 비율 계산 & 시각화
   - 불균형 감지 시 Agent 개입 트리거

3. **회의 종료 처리**
   - 리캡 생성
   - Action Item 자동 추출
   - Markdown 파일 저장

### Phase 4: 마무리 (1시간)
```
Priority: MEDIUM
목표: 데모 준비
```

1. **데모 시뮬레이션 모드**
   - 미리 준비된 스크립트 재생
   - 수동 트리거 버튼

2. **UI 폴리싱**
   - 애니메이션
   - 에러 처리 UI

---

## 2. 기술 스택 상세

### Frontend
```json
{
  "framework": "Next.js 14",
  "language": "TypeScript",
  "styling": "Tailwind CSS",
  "components": "shadcn/ui",
  "state": "Zustand (권장) 또는 React Context",
  "audio": "Web Audio API + MediaRecorder",
  "websocket": "native WebSocket",
  "alertSound": "HTML5 Audio API"
}
```

### Backend
```json
{
  "framework": "Python 3.12 + OpenAI Agents SDK",
  "webServer": "FastAPI (필요시)",
  "websocket": "websockets / fastapi.WebSocket",
  "ai": "OpenAI Agents SDK",
  "async": "asyncio",
  "storage": "로컬 파일시스템 (.md)"
}
```

### OpenAI APIs
```json
{
  "stt": "OpenAI Realtime API (WebSocket 기반 실시간 STT)",
  "llm": "gpt-5.2 (Agent 추론, 원칙 위반 감지, 화자 분리)",
  "agents": "OpenAI Agents SDK (Multi-Agent 오케스트레이션)"
}
```

> **참고**: TTS는 사용하지 않음. 개입 시 **짧고 부드러운 차임벨 (1초 이내)** + Toast 메시지 방식 사용.

---

## 3. 프로젝트 구조

```
meetingmod/
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   │
│   ├── app/
│   │   ├── layout.tsx              # Root layout
│   │   ├── page.tsx                # 회의 준비 화면
│   │   ├── principles/
│   │   │   └── page.tsx            # 회의 원칙 관리
│   │   ├── meeting/
│   │   │   └── [id]/
│   │   │       └── page.tsx        # 회의 진행 화면
│   │   └── review/
│   │       └── [id]/
│   │           └── page.tsx        # 회의 결과 화면
│   │
│   ├── components/
│   │   ├── ui/                     # shadcn components
│   │   ├── meeting-prep-form.tsx   # 회의 준비 폼
│   │   ├── markdown-editor.tsx     # 아젠다 에디터
│   │   ├── participant-list.tsx    # 참석자 목록
│   │   ├── principle-editor.tsx    # 원칙 편집기
│   │   ├── meeting-room.tsx        # 회의 진행 메인
│   │   ├── transcript-view.tsx     # 실시간 자막 (화자명 포함)
│   │   ├── speaker-stats.tsx       # 발언 통계 시각화
│   │   ├── intervention-toast.tsx  # Agent 개입 알림
│   │   ├── alert-sound.tsx         # 경고음 컴포넌트
│   │   ├── agenda-tracker.tsx      # 아젠다 진행상황
│   │   └── meeting-controls.tsx    # 컨트롤 버튼
│   │
│   ├── lib/
│   │   ├── websocket.ts            # WebSocket 클라이언트
│   │   ├── audio-capture.ts        # 마이크 캡처
│   │   ├── sound-player.ts         # 경고음 재생
│   │   └── utils.ts                # 유틸리티
│   │
│   ├── hooks/
│   │   ├── use-websocket.ts        # WebSocket hook
│   │   ├── use-audio.ts            # 오디오 hook
│   │   └── use-meeting.ts          # 회의 상태 hook
│   │
│   ├── store/
│   │   └── meeting-store.ts        # Zustand store
│   │
│   └── public/
│       └── sounds/
│           └── alert.wav           # 경고음 파일
│
├── backend/
│   ├── requirements.txt
│   ├── main.py                     # 엔트리포인트 (OpenAI Agents SDK)
│   │
│   ├── server.py                   # FastAPI 서버 (필요시)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Orchestrator Agent
│   │   ├── prep_agent.py           # Prep Agent
│   │   ├── moderator_agent.py      # Moderator Agent (핵심)
│   │   └── review_agent.py         # Review Agent
│   │
│   ├── services/
│   │   ├── stt_service.py          # Whisper STT
│   │   ├── speaker_service.py      # AI 화자 분리
│   │   └── storage_service.py      # Markdown 파일 저장
│   │
│   └── models/
│       ├── meeting.py              # 회의 모델
│       └── intervention.py         # 개입 모델
│
├── meetings/                        # 회의 데이터 저장
│   └── {YYYY-MM-DD-meeting-title}/
│       ├── preparation.md          # 회의 준비 자료
│       ├── principles.md           # 적용된 회의 원칙
│       ├── transcript.md           # 녹취록 (화자 포함)
│       ├── interventions.md        # Agent 개입 기록
│       ├── summary.md              # 회의 요약
│       └── action-items.md         # Action Items
│
└── principles/                      # 회의 원칙 템플릿
    ├── agile.md
    └── aws-leadership.md
```

---

## 4. 핵심 구현 가이드

### 4.1 WebSocket 연결

**Frontend (lib/websocket.ts)**
```typescript
export class MeetingWebSocket {
  private ws: WebSocket | null = null;
  private meetingId: string;
  private onMessage: (message: any) => void;

  constructor(meetingId: string, onMessage: (message: any) => void) {
    this.meetingId = meetingId;
    this.onMessage = onMessage;
  }

  connect() {
    this.ws = new WebSocket(`ws://localhost:8000/ws/meetings/${this.meetingId}`);

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.onMessage(message);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  sendAudio(audioData: Blob) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      // Convert to base64 and send
      const reader = new FileReader();
      reader.onloadend = () => {
        this.ws?.send(JSON.stringify({
          type: 'audio',
          data: reader.result,
          timestamp: Date.now()
        }));
      };
      reader.readAsDataURL(audioData);
    }
  }

  disconnect() {
    this.ws?.close();
  }
}
```

**Backend (routers/websocket.py)**
```python
from fastapi import WebSocket, WebSocketDisconnect
from agents.moderator_agent import ModeratorAgent
from services.stt_service import STTService

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, meeting_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[meeting_id] = websocket

    async def disconnect(self, meeting_id: str):
        if meeting_id in self.active_connections:
            del self.active_connections[meeting_id]

    async def send_message(self, meeting_id: str, message: dict):
        if meeting_id in self.active_connections:
            await self.active_connections[meeting_id].send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/meetings/{meeting_id}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str):
    await manager.connect(meeting_id, websocket)
    stt_service = STTService()
    moderator = ModeratorAgent(meeting_id)

    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "audio":
                # STT 처리
                transcript = await stt_service.transcribe(data["data"])

                # 자막 전송
                await manager.send_message(meeting_id, {
                    "type": "transcript",
                    "data": transcript
                })

                # Agent 분석 (버퍼에 축적)
                intervention = await moderator.analyze(transcript)
                if intervention:
                    await manager.send_message(meeting_id, {
                        "type": "intervention",
                        "data": intervention
                    })

    except WebSocketDisconnect:
        await manager.disconnect(meeting_id)
```

### 4.2 Moderator Agent 구현 (발화 멈춤 감지 + 경고음)

**agents/moderator_agent.py**
```python
from openai import OpenAI
import json
import time
import uuid
from datetime import datetime

class ModeratorAgent:
    def __init__(self, meeting_id: str):
        self.client = OpenAI()
        self.meeting_id = meeting_id
        self.transcript_buffer = []
        self.agenda = []
        self.principles = []
        self.participants = []
        self.speaker_stats = {}
        self.last_intervention_time = 0
        self.last_speech_time = 0
        self.silence_threshold = 1.5  # 1.5초 침묵 시 개입 판단

    def set_context(self, agenda: list, principles: list, participants: list):
        self.agenda = agenda
        self.principles = principles
        self.participants = participants

    async def on_speech_end(self, silence_duration: float) -> dict | None:
        """
        발화자가 말을 멈췄을 때 호출됨.
        silence_duration: 침묵 지속 시간 (초)
        """
        if silence_duration < self.silence_threshold:
            return None

        # 최소 개입 간격 체크 (20초)
        current_time = time.time()
        if current_time - self.last_intervention_time < 20:
            return None

        # 개입 필요성 판단
        intervention = await self._check_intervention()
        if intervention:
            self.last_intervention_time = current_time
            # 개입 시 경고음 재생 플래그 포함
            intervention["playAlertSound"] = True
            return intervention

        return None

    async def add_transcript(self, transcript_entry: dict):
        """새 발화 추가"""
        self.transcript_buffer.append(transcript_entry)
        self._update_speaker_stats(transcript_entry)
        self.last_speech_time = time.time()

    async def _check_intervention(self) -> dict | None:
        """GPT-4o로 개입 필요성 분석"""
        if len(self.transcript_buffer) < 3:
            return None

        recent_transcript = self.transcript_buffer[-10:]  # 최근 10개 발화

        system_prompt = f"""You are an AI meeting moderator.
Your role is to monitor the meeting and intervene actively when the speaker stops talking.

Meeting agenda: {json.dumps(self.agenda, ensure_ascii=False)}
Meeting principles: {json.dumps(self.principles, ensure_ascii=False)}
Participants: {json.dumps(self.participants, ensure_ascii=False)}
Speaker statistics: {json.dumps(self.speaker_stats, ensure_ascii=False)}

Analyze the recent conversation and determine if intervention is needed.
BE PROACTIVE - intervene when you detect issues.

Intervention types:
- TOPIC_DRIFT: When discussion goes off-topic (respond with parking lot suggestion)
- PRINCIPLE_VIOLATION: When someone violates meeting principles (e.g., top-down decision, not respecting others)
- PARTICIPATION_IMBALANCE: When participation is uneven (one person dominates, someone hasn't spoken)
- DECISION_STYLE: When top-down decision making is detected (if horizontal decision is a principle)

INTERVENTION TONE: Be DIRECT and COURAGEOUS. Examples:
- BAD: "재미있는 이야기네요! 다만 시간 관계상..."
- GOOD: "잠깐요, 아젠다에서 벗어났어요. 돌아갈게요."
- BAD: "의견이 있으실까요?"
- GOOD: "잠깐요! 아직 발언 안 하셨어요. 어떻게 보세요?"
- BAD: "다른 분들 의견은 어떠신가요?"
- GOOD: "멈춰주세요! 원칙 위반입니다. 다른 분들 동의하시나요?"

Respond in JSON format:
{{
  "needs_intervention": true/false,
  "intervention_type": "TOPIC_DRIFT" | "PRINCIPLE_VIOLATION" | "PARTICIPATION_IMBALANCE" | "DECISION_STYLE" | null,
  "message": "개입 메시지 (한국어, 직접적이고 용기있는 톤)",
  "violated_principle": "위반된 원칙명" | null,
  "parking_lot_item": "주제 이탈 시 추가할 항목" | null,
  "suggested_speaker": "발언 권유할 참석자 이름" | null
}}
"""

        response = self.client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(recent_transcript, ensure_ascii=False)}
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        if result.get("needs_intervention"):
            return {
                "id": f"int_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.utcnow().isoformat(),
                "type": result["intervention_type"],
                "message": result["message"],
                "violatedPrinciple": result.get("violated_principle"),
                "parkingLotItem": result.get("parking_lot_item"),
                "suggestedSpeaker": result.get("suggested_speaker"),
                "triggerContext": recent_transcript[-1].get("text", "") if recent_transcript else ""
            }

        return None

    def _update_speaker_stats(self, entry: dict):
        speaker = entry.get("speaker", "Unknown")
        text_length = len(entry.get("text", ""))
        duration = entry.get("duration", 0)

        if speaker not in self.speaker_stats:
            self.speaker_stats[speaker] = {
                "count": 0,
                "chars": 0,
                "duration": 0
            }

        self.speaker_stats[speaker]["count"] += 1
        self.speaker_stats[speaker]["chars"] += text_length
        self.speaker_stats[speaker]["duration"] += duration
```

### 4.3 Audio Capture (Frontend) + 침묵 감지

**lib/audio-capture.ts**
```typescript
export class AudioCapture {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private onDataAvailable: (data: Blob) => void;
  private onSilenceDetected: (silenceDuration: number) => void;
  private silenceStart: number | null = null;
  private silenceThreshold = 0.01; // 볼륨 임계값

  constructor(
    onDataAvailable: (data: Blob) => void,
    onSilenceDetected: (silenceDuration: number) => void
  ) {
    this.onDataAvailable = onDataAvailable;
    this.onSilenceDetected = onSilenceDetected;
  }

  async start() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // 침묵 감지를 위한 AudioContext 설정
      this.audioContext = new AudioContext();
      const source = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      source.connect(this.analyser);

      // 침묵 감지 시작
      this.detectSilence();

      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.onDataAvailable(event.data);
        }
      };

      // 3초마다 청크 전송
      this.mediaRecorder.start(3000);
    } catch (error) {
      console.error('Failed to start audio capture:', error);
      throw error;
    }
  }

  private detectSilence() {
    if (!this.analyser) return;

    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const checkVolume = () => {
      if (!this.analyser) return;

      this.analyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / bufferLength / 255;

      if (average < this.silenceThreshold) {
        // 침묵 시작 또는 지속
        if (this.silenceStart === null) {
          this.silenceStart = Date.now();
        } else {
          const silenceDuration = (Date.now() - this.silenceStart) / 1000;
          // 1.5초 이상 침묵 시 콜백 호출
          if (silenceDuration >= 1.5) {
            this.onSilenceDetected(silenceDuration);
            this.silenceStart = null; // 리셋
          }
        }
      } else {
        // 소리 감지됨 - 침묵 리셋
        this.silenceStart = null;
      }

      requestAnimationFrame(checkVolume);
    };

    checkVolume();
  }

  stop() {
    this.mediaRecorder?.stop();
    this.stream?.getTracks().forEach(track => track.stop());
    this.audioContext?.close();
  }

  pause() {
    this.mediaRecorder?.pause();
  }

  resume() {
    this.mediaRecorder?.resume();
  }
}
```

### 4.4 경고음 재생

**경고음 스펙**
- **타입**: 짧고 부드러운 차임벨
- **길이**: 1초 이내
- **볼륨**: 0.7 (70%)
- **파일**: `/public/sounds/alert-chime.wav`
- **권장 소스**:
  - https://freesound.org (검색: "soft chime notification")
  - https://mixkit.co/free-sound-effects/notification/
  - https://notificationsounds.com/notification-sounds

**lib/sound-player.ts**
```typescript
export class SoundPlayer {
  private audio: HTMLAudioElement;
  private isReady: boolean = false;

  constructor() {
    // 짧고 부드러운 차임벨 (1초 이내)
    this.audio = new Audio('/sounds/alert-chime.wav');
    this.audio.volume = 0.7;

    // 프리로드하여 지연 최소화
    this.audio.addEventListener('canplaythrough', () => {
      this.isReady = true;
    });
    this.audio.load();
  }

  playAlert() {
    if (!this.isReady) {
      console.warn('Alert sound not ready yet');
      return;
    }
    this.audio.currentTime = 0;
    this.audio.play().catch(err => {
      console.warn('Alert sound failed to play:', err);
    });
  }

  // 볼륨 조절 (0.0 ~ 1.0)
  setVolume(volume: number) {
    this.audio.volume = Math.max(0, Math.min(1, volume));
  }
}
```

**components/intervention-toast.tsx**
```typescript
import { useEffect } from 'react';
import { Toast, ToastTitle, ToastDescription } from '@/components/ui/toast';
import { SoundPlayer } from '@/lib/sound-player';

interface InterventionToastProps {
  intervention: {
    type: string;
    message: string;
    playAlertSound?: boolean;
  } | null;
  onClose: () => void;
}

const soundPlayer = new SoundPlayer();

export function InterventionToast({ intervention, onClose }: InterventionToastProps) {
  useEffect(() => {
    if (intervention?.playAlertSound) {
      soundPlayer.playAlert();
    }
  }, [intervention]);

  if (!intervention) return null;

  const typeLabels = {
    TOPIC_DRIFT: '🎯 주제 이탈',
    PRINCIPLE_VIOLATION: '⚠️ 원칙 위반',
    PARTICIPATION_IMBALANCE: '⚖️ 발언 불균형',
    DECISION_STYLE: '🤝 의사결정 방식'
  };

  return (
    <Toast open={!!intervention} onOpenChange={() => onClose()}>
      <ToastTitle>{typeLabels[intervention.type] || '🤖 AI 개입'}</ToastTitle>
      <ToastDescription>{intervention.message}</ToastDescription>
    </Toast>
  );
}
```

### 4.5 Realtime API STT Service (Backend)

**services/realtime_stt_service.py**
```python
import asyncio
import websockets
import json
import uuid
from datetime import datetime
from typing import Callable, Optional

REALTIME_API_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"

class RealtimeSTTService:
    """OpenAI Realtime API 기반 실시간 STT 서비스"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.on_transcript: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None

    async def connect(self, on_transcript: Callable, on_speech_end: Callable):
        """Realtime API 연결 및 세션 설정"""
        self.on_transcript = on_transcript
        self.on_speech_end = on_speech_end

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

        self.ws = await websockets.connect(
            REALTIME_API_URL,
            extra_headers=headers
        )

        # 세션 설정: 실시간 전사 + 1.5초 침묵 감지
        await self.ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "input_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 1500  # 1.5초 침묵 시 발화 종료 감지
                }
            }
        }))

        # 메시지 수신 루프 시작
        asyncio.create_task(self._receive_loop())

    async def _receive_loop(self):
        """Realtime API 메시지 수신 루프"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                event_type = data.get("type", "")

                # 실시간 전사 완료
                if event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = data.get("transcript", "")
                    if transcript and self.on_transcript:
                        await self.on_transcript({
                            "id": f"tr_{uuid.uuid4().hex[:8]}",
                            "text": transcript,
                            "timestamp": datetime.utcnow().isoformat(),
                            "isFinal": True
                        })

                # 발화 종료 감지 (침묵 1.5초)
                elif event_type == "input_audio_buffer.speech_stopped":
                    if self.on_speech_end:
                        await self.on_speech_end()

        except websockets.exceptions.ConnectionClosed:
            print("Realtime API connection closed")

    async def send_audio(self, audio_base64: str):
        """오디오 청크 전송"""
        if self.ws:
            await self.ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }))

    async def disconnect(self):
        """연결 종료"""
        if self.ws:
            await self.ws.close()
```

**services/speaker_service.py**
```python
from openai import OpenAI
import json

class SpeakerService:
    """GPT-5.2 기반 화자 분리 서비스"""

    def __init__(self):
        self.client = OpenAI()
        self.participants = []
        self.recent_speakers = []  # 최근 화자 기록

    def set_participants(self, participants: list):
        """참석자 목록 설정"""
        self.participants = participants

    async def identify_speaker(self, text: str, context: list[dict]) -> dict:
        """
        발화 텍스트와 컨텍스트를 기반으로 화자 추론 (GPT-5.2 활용).
        context: 최근 발화 기록 (speaker, text)
        """
        if not self.participants:
            return {"speaker": "Unknown", "confidence": 0.0}

        participant_info = json.dumps(
            [{"name": p["name"], "role": p["role"]} for p in self.participants],
            ensure_ascii=False
        )

        recent_context = json.dumps(context[-5:], ensure_ascii=False) if context else "[]"

        prompt = f"""You are a speaker identification AI using GPT-5.2's advanced context understanding.
Based on the participant list, recent conversation context, and the new utterance,
identify who is most likely speaking.

Participants:
{participant_info}

Recent conversation (for context):
{recent_context}

New utterance to identify:
"{text}"

Consider:
1. Speaking patterns and vocabulary
2. Role-appropriate topics (e.g., PM talks about deadlines, developer talks about code)
3. Conversation flow (who would logically respond)
4. Korean honorifics and speech patterns
5. Emotional tone and formality level

Respond in JSON format:
{{
  "speaker": "화자 이름 (from participant list)",
  "confidence": 0.0-1.0,
  "reasoning": "간단한 추론 이유"
}}
"""

        response = self.client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # 화자 기록 업데이트
        self.recent_speakers.append(result["speaker"])
        if len(self.recent_speakers) > 10:
            self.recent_speakers.pop(0)

        return {
            "speaker": result["speaker"],
            "confidence": result["confidence"]
        }
```

### 4.6 Markdown 파일 저장 서비스

**services/storage_service.py**
```python
import os
from datetime import datetime
from pathlib import Path

class StorageService:
    """Markdown 파일 저장 서비스"""

    def __init__(self, base_path: str = "meetings"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def get_meeting_dir(self, meeting_id: str) -> Path:
        """회의 디렉토리 경로 반환 (없으면 생성)"""
        meeting_dir = self.base_path / meeting_id
        meeting_dir.mkdir(exist_ok=True)
        return meeting_dir

    async def save_transcript(self, meeting_id: str, entries: list[dict], title: str):
        """녹취록 저장"""
        meeting_dir = self.get_meeting_dir(meeting_id)
        filepath = meeting_dir / "transcript.md"

        content = f"""# 회의 녹취록

회의: {title}
일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

"""
        for entry in entries:
            timestamp = entry.get("timestamp", "")[:19].replace("T", " ")
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "")
            content += f"[{timestamp}] **{speaker}**: {text}\n\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    async def save_interventions(self, meeting_id: str, interventions: list[dict], title: str):
        """개입 기록 저장"""
        meeting_dir = self.get_meeting_dir(meeting_id)
        filepath = meeting_dir / "interventions.md"

        content = f"""# Agent 개입 기록

회의: {title}
생성일: {datetime.now().strftime('%Y-%m-%d')}

---

"""
        for idx, inv in enumerate(interventions, 1):
            content += f"""## 개입 #{idx}

- **시간**: {inv.get("timestamp", "")[:19].replace("T", " ")}
- **유형**: {inv.get("type", "")}
- **메시지**: {inv.get("message", "")}
"""
            if inv.get("violatedPrinciple"):
                content += f"- **위반 원칙**: {inv['violatedPrinciple']}\n"
            if inv.get("parkingLotItem"):
                content += f"- **Parking Lot**: {inv['parkingLotItem']}\n"
            content += "\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    async def save_action_items(self, meeting_id: str, items: list[dict], title: str):
        """Action Items 저장"""
        meeting_dir = self.get_meeting_dir(meeting_id)
        filepath = meeting_dir / "action-items.md"

        content = f"""# Action Items

회의: {title}
생성일: {datetime.now().strftime('%Y-%m-%d')}

---

## 할당된 업무

"""
        for idx, item in enumerate(items, 1):
            content += f"""### {idx}. {item.get("description", "")}
- **담당**: {item.get("assignee", "미정")}
- **기한**: {item.get("dueDate", "미정")}
- **맥락**: {item.get("context", "")}

"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    async def save_summary(self, meeting_id: str, summary: str, title: str):
        """회의 요약 저장"""
        meeting_dir = self.get_meeting_dir(meeting_id)
        filepath = meeting_dir / "summary.md"

        content = f"""# 회의 요약

회의: {title}
생성일: {datetime.now().strftime('%Y-%m-%d')}

---

{summary}
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
```

---

## 5. 환경 설정

### Frontend (.env.local)
```env
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Backend (.env)
```env
OPENAI_API_KEY=sk-xxx
CORS_ORIGINS=http://localhost:3000
DEBUG=true
```

### 필수 패키지

**Frontend (package.json dependencies)**
```json
{
  "next": "^14.0.0",
  "react": "^18.2.0",
  "typescript": "^5.0.0",
  "tailwindcss": "^3.4.0",
  "@radix-ui/react-*": "latest",
  "zustand": "^4.5.0",
  "lucide-react": "latest",
  "class-variance-authority": "latest",
  "clsx": "latest"
}
```

**Backend (requirements.txt)**
```
openai-agents>=0.1.0
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
websockets>=12.0
openai>=1.10.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

> **참고**: Python 3.12 사용. `openai-agents`는 OpenAI Agents SDK.

---

## 6. 실행 명령어

### Frontend
```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
# 또는 FastAPI 사용 시:
# uvicorn server:app --reload --port 8000
# http://localhost:8000
```

> **참고**: Python 3.12 필수. OpenAI Agents SDK 사용.

---

## 7. 데모 시뮬레이션 모드

해커톤 발표 시 안정적인 데모를 위해 시뮬레이션 모드 구현:

**frontend/lib/demo-simulator.ts**
```typescript
export const demoScript = [
  { speaker: "김철수", text: "지난 스프린트에서 8개 태스크를 완료했습니다.", delay: 0 },
  { speaker: "이민수", text: "네, 성과가 좋았어요.", delay: 3000 },
  { speaker: "이민수", text: "그런데 점심 뭐 먹을까요?", delay: 6000, triggerIntervention: "TOPIC_DRIFT" },
  { speaker: "김철수", text: "아, 네. 다음 스프린트 계획을 보면...", delay: 12000 },
  { speaker: "김철수", text: "이번 스프린트는 API 최적화에 집중합시다.", delay: 15000 },
  { speaker: "김철수", text: "박영희 씨, 동의하시죠?", delay: 18000, triggerIntervention: "DECISION_STYLE" },
  // ... 추가 시나리오
];

export class DemoSimulator {
  private scriptIndex = 0;
  private onTranscript: (entry: any) => void;
  private onIntervention: (intervention: any) => void;
  private soundPlayer: { playAlert: () => void };

  constructor(
    onTranscript: (entry: any) => void,
    onIntervention: (intervention: any) => void,
    soundPlayer: { playAlert: () => void }
  ) {
    this.onTranscript = onTranscript;
    this.onIntervention = onIntervention;
    this.soundPlayer = soundPlayer;
  }

  start() {
    this.playNext();
  }

  private playNext() {
    if (this.scriptIndex >= demoScript.length) return;

    const entry = demoScript[this.scriptIndex];

    setTimeout(() => {
      this.onTranscript({
        speaker: entry.speaker,
        text: entry.text,
        timestamp: new Date().toISOString()
      });

      if (entry.triggerIntervention) {
        // 발화 멈춤 후 1.5초 뒤 개입 (침묵 감지 시뮬레이션)
        setTimeout(() => {
          // 경고음 재생
          this.soundPlayer.playAlert();
          // Toast 표시
          this.onIntervention(this.getIntervention(entry.triggerIntervention));
        }, 1500);
      }

      this.scriptIndex++;
      this.playNext();
    }, entry.delay);
  }

  private getIntervention(type: string) {
    const interventions: Record<string, any> = {
      TOPIC_DRIFT: {
        id: "int_demo_001",
        type: "TOPIC_DRIFT",
        message: "재미있는 이야기네요! 다만 시간 관계상, 현재 논의 중인 '스프린트 계획'을 먼저 마무리하면 어떨까요?",
        parkingLotItem: "점심 메뉴",
        playAlertSound: true
      },
      DECISION_STYLE: {
        id: "int_demo_002",
        type: "DECISION_STYLE",
        message: "잠깐요! 중요한 결정 전에, 아직 의견을 말씀하지 않으신 박영희 님의 생각도 들어보면 어떨까요?",
        violatedPrinciple: "수평적 의사결정",
        suggestedSpeaker: "박영희",
        playAlertSound: true
      },
      PARTICIPATION_IMBALANCE: {
        id: "int_demo_003",
        type: "PARTICIPATION_IMBALANCE",
        message: "지금까지 김철수 님이 발언의 70%를 차지하고 계세요. 다른 분들의 의견도 들어볼까요?",
        playAlertSound: true
      },
      PRINCIPLE_VIOLATION: {
        id: "int_demo_004",
        type: "PRINCIPLE_VIOLATION",
        message: "말씀 중에 죄송합니다. 'Disagree and Commit' 원칙에 따라, 이견이 있으시면 지금 말씀해 주세요.",
        violatedPrinciple: "Disagree and Commit",
        playAlertSound: true
      }
    };
    return interventions[type] || interventions.TOPIC_DRIFT;
  }
}
```

---

## 8. 핵심 구현 체크리스트

### Phase 1 체크리스트
- [ ] Next.js 14 프로젝트 생성 (`npx create-next-app@latest`)
- [ ] shadcn/ui 설치 (`npx shadcn-ui@latest init`)
- [ ] Python 3.12 환경 구성
- [ ] OpenAI Agents SDK 설치
- [ ] 기본 레이아웃 및 라우팅 구조

### Phase 2 체크리스트
- [ ] WebSocket 연결 (Frontend ↔ Backend)
- [ ] 마이크 오디오 캡처 (Web Audio API)
- [ ] 침묵 감지 로직 (1.5초 임계값)
- [ ] Whisper STT 연동 (한국어)
- [ ] AI 화자 분리 서비스
- [ ] Moderator Agent 구현 (발화 멈춤 시 개입)
- [ ] 경고음 재생 컴포넌트
- [ ] Toast 개입 메시지 UI

### Phase 3 체크리스트
- [ ] 회의 원칙 관리 페이지 (`/principles`)
- [ ] Agile/AWS LP 템플릿
- [ ] 발언 통계 시각화 (Progress Bar)
- [ ] 회의 종료 → 리캡 생성
- [ ] Action Item 추출 (LLM)
- [ ] Markdown 파일 저장

### Phase 4 체크리스트
- [ ] 데모 시뮬레이션 모드
- [ ] 데모 스크립트 준비
- [ ] UI 폴리싱 및 에러 처리
- [ ] 발표 리허설

---

## 9. 개입 타이밍 플로우차트

```
┌─────────────────────────────────────────────────────────────────┐
│                     실시간 음성 처리 파이프라인                      │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────┐
│ 마이크 오디오 캡처 │
│ (Web Audio API) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ WebSocket 전송   │────▶│ Whisper STT     │
│ (3초 청크)       │     │ (한국어 변환)     │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ AI 화자 분리     │
                        │ (GPT-4o)        │
                        └────────┬────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         │                                               │
         ▼                                               ▼
┌─────────────────┐                           ┌─────────────────┐
│ 실시간 자막 표시  │                           │ 침묵 감지        │
│ (화자명 + 발화)  │                           │ (1.5초 임계값)   │
└─────────────────┘                           └────────┬────────┘
                                                       │
                                              침묵 1.5초 이상?
                                                       │
                                    ┌──────────────────┴──────────────────┐
                                    │                                     │
                                   No                                    Yes
                                    │                                     │
                                    ▼                                     ▼
                           다음 발화 대기                        ┌─────────────────┐
                                                                │ Moderator Agent │
                                                                │ 개입 분석       │
                                                                └────────┬────────┘
                                                                         │
                                                              개입 필요?
                                                                         │
                                                    ┌────────────────────┴────────────────────┐
                                                    │                                         │
                                                   No                                        Yes
                                                    │                                         │
                                                    ▼                                         ▼
                                           다음 발화 대기                            ┌─────────────────┐
                                                                                    │ 경고음 재생 🔔   │
                                                                                    │ + Toast 표시    │
                                                                                    └─────────────────┘
```
