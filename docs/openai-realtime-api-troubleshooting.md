# OpenAI Realtime API 연동 트러블슈팅 가이드

이 문서는 OpenAI Realtime API를 사용한 실시간 음성 인식(STT) 구현 과정에서 발생한 주요 이슈와 해결 방법을 기록합니다.

## 목차

1. [아키텍처 개요](#아키텍처-개요)
2. [주요 이슈 및 해결](#주요-이슈-및-해결)
3. [디버깅 체크리스트](#디버깅-체크리스트)
4. [OpenAI Realtime API 설정](#openai-realtime-api-설정)

---

## 아키텍처 개요

```
[Browser] --WebSocket--> [FastAPI Backend] --WebSocket--> [OpenAI Realtime API]
   |                            |                                |
   | PCM16 Audio               | Forward Audio                 | Transcription
   | (24kHz)                   |                                |
   |<-- Transcript ------------|<-- Transcript ----------------|
```

- **Frontend**: Next.js + Web Audio API로 마이크 캡처
- **Backend**: FastAPI WebSocket 핸들러
- **OpenAI**: Realtime API (gpt-4o-realtime-preview)

---

## 주요 이슈 및 해결

### 1. websockets 라이브러리 버전 호환성

**증상**: `BaseEventLoop.create_connection() got an unexpected keyword argument 'extra_headers'`

**원인**: websockets 16.0에서 파라미터 이름이 변경됨

**해결**:
```python
# Before (websockets < 16.0)
await websockets.connect(url, extra_headers=headers)

# After (websockets >= 16.0)
await websockets.connect(url, additional_headers=headers)
```

---

### 2. 오디오 포맷 불일치

**증상**: 오디오 청크가 백엔드로 전송되지만 transcription이 발생하지 않음

**원인**: OpenAI Realtime API는 **PCM16 @ 24kHz**만 지원하는데, 브라우저 MediaRecorder는 기본적으로 webm/opus 포맷을 출력

**해결**: Web Audio API를 사용하여 직접 PCM16 변환

프론트엔드에서 필요한 변환:
1. `AudioContext`를 24kHz 샘플레이트로 생성
2. `ScriptProcessorNode`로 raw Float32 오디오 데이터 캡처
3. Float32 → Int16(PCM16) 변환
4. Int16 → Base64 인코딩 후 전송

**핵심 변환 로직**:
```typescript
// Float32 (-1.0 ~ 1.0) → Int16 (-32768 ~ 32767)
const floatTo16BitPCM = (float32Array: Float32Array): Int16Array => {
  const int16Array = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return int16Array;
};
```

**주의사항**:
- MediaRecorder API로는 PCM16 출력이 불가능 (브라우저 제한)
- ScriptProcessorNode는 deprecated이지만 아직 널리 지원됨
- AudioWorklet은 더 현대적이지만 설정이 복잡함

---

### 3. WebSocket readyState 이해

**증상**: 프론트엔드에서 "WebSocket connection error occurred, readyState: 3"

**readyState 값**:
- `0` (CONNECTING): 연결 시도 중
- `1` (OPEN): 연결됨, 통신 가능
- `2` (CLOSING): 연결 종료 중
- `3` (CLOSED): 연결 종료됨

**디버깅 팁**:
- `readyState: 3`이면 연결이 즉시 닫힌 것
- 백엔드 로그와 프론트엔드 콘솔을 동시에 확인
- 여러 연결 시도가 발생할 수 있음 (React re-render)

---

### 4. React 하이드레이션 오류

**증상**: "Hydration failed because the server rendered HTML didn't match the client"

**원인**: 브라우저 확장 프로그램(영한사전 등)이 DOM을 수정

**해결**: 기능에는 영향 없음, 무시 가능. 필요시 시크릿 모드에서 테스트.

---

### 5. React Hook 중복 실행 방지

**증상**: WebSocket이 여러 번 연결되거나 오디오 캡처가 중복 시작됨

**원인**: React Strict Mode에서 useEffect가 두 번 실행되거나, 의존성 배열 문제

**해결**: Ref를 사용한 초기화 플래그
```typescript
const initializedRef = useRef(false);

useEffect(() => {
  if (initializedRef.current) return;
  initializedRef.current = true;

  // 초기화 로직

  return () => {
    initializedRef.current = false;
  };
}, []);
```

---

### 6. 미정의 변수 참조 (speaker_result)

**증상**: 백엔드에서 transcription 수신 후 프론트엔드로 전송되지 않음

**원인**: 코드 리팩토링 중 변수 참조 오류
```python
# 버그: speaker_result가 정의되지 않음
entry = TranscriptEntry(
    confidence=speaker_result["confidence"],  # NameError!
)
```

**해결**: 사용하지 않는 변수 참조 제거
```python
entry = TranscriptEntry(
    confidence=1.0,  # 기본값 사용
)
```

**교훈**: 코드 간소화 시 모든 참조를 확인할 것

---

## 디버깅 체크리스트

### 자막이 표시되지 않을 때

1. **백엔드 로그 확인**
   ```bash
   tail -f /tmp/server.log
   ```

   확인 사항:
   - [ ] "WebSocket ... [accepted]" 로그가 있는가?
   - [ ] "Audio chunk #N received" 로그가 있는가?
   - [ ] "TRANSCRIPT RECEIVED" 로그가 있는가?
   - [ ] "Transcript sent successfully" 로그가 있는가?

2. **단계별 문제 진단**

   | 로그 없음 | 문제 영역 |
   |-----------|-----------|
   | WebSocket accepted 없음 | 프론트엔드 → 백엔드 연결 문제 |
   | Audio chunk 없음 | 프론트엔드 오디오 캡처 또는 전송 문제 |
   | TRANSCRIPT 없음 | 백엔드 → OpenAI 연결 또는 오디오 포맷 문제 |
   | Sent successfully 없음 | 백엔드 코드 오류 |

3. **독립 테스트 페이지 사용**

   `/test` 엔드포인트의 HTML 테스트 페이지로 Next.js를 거치지 않고 직접 테스트:
   ```
   http://localhost:8000/test
   ```

---

## OpenAI Realtime API 설정

### 세션 구성

```python
session_config = {
    "type": "session.update",
    "session": {
        "modalities": ["text", "audio"],
        "input_audio_format": "pcm16",  # 필수: PCM16 포맷
        "input_audio_transcription": {
            "model": "whisper-1"  # 전사 모델
        },
        "turn_detection": {
            "type": "server_vad",      # Voice Activity Detection
            "threshold": 0.5,           # 민감도 (0.0 ~ 1.0)
            "prefix_padding_ms": 300,   # 발화 시작 전 버퍼
            "silence_duration_ms": 1500 # 침묵 감지 시간
        },
    },
}
```

### 주요 이벤트

| 이벤트 | 설명 |
|--------|------|
| `session.created` | 세션 생성 완료 |
| `session.updated` | 세션 설정 업데이트 완료 |
| `input_audio_buffer.speech_started` | 발화 시작 감지 |
| `input_audio_buffer.speech_stopped` | 발화 종료 감지 |
| `conversation.item.input_audio_transcription.completed` | **전사 완료 (핵심!)** |
| `conversation.item.input_audio_transcription.failed` | 전사 실패 |

### 오디오 전송

```python
await ws.send(json.dumps({
    "type": "input_audio_buffer.append",
    "audio": base64_pcm16_audio
}))
```

---

## 권장 로깅

### 백엔드 로깅 포인트

```python
# WebSocket 연결
logger.info(f"WebSocket endpoint called for meeting: {meeting_id}")
logger.info(f"WebSocket connected for meeting: {meeting_id}")

# 오디오 수신
logger.info(f"Audio chunk #{count} received, size: {size} bytes")

# 전사 수신
logger.info(f"=== TRANSCRIPT RECEIVED: '{text}' ===")

# 프론트엔드 전송
logger.info(f"Sending transcript to frontend")
logger.info(f"Transcript sent successfully")
```

### 프론트엔드 로깅 포인트

```typescript
// WebSocket
console.log("Connecting to WebSocket:", fullUrl);
console.log("WebSocket connected successfully, readyState:", ws.readyState);
console.error("WebSocket connection error occurred, readyState:", ws.readyState);

// 오디오
console.log("Audio capture started (PCM16 @ 24kHz)");

// 메시지 수신
console.log("Received:", message.type, message.data);
```

---

## 참고 자료

- [OpenAI Realtime API Documentation](https://platform.openai.com/docs/guides/realtime)
- [Web Audio API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [WebSocket API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
