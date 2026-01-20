# MeetingMod - Technical Architecture

## 1. Multi-Agent 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator Agent                          │
│              (회의 상태 관리, Agent 간 조율, 의사결정)              │
└─────────────────────────────────────────────────────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Prep Agent    │   │ Moderator Agent │   │  Review Agent   │
│                 │   │                 │   │                 │
│ • 준비 자료 검증  │   │ • 실시간 분석     │   │ • 회의록 생성     │
│ • 참석자 관리     │   │ • 개입 판단      │   │ • Action Item   │
│ • 원칙 로드       │   │ • 화자 분리      │   │ • 피드백 생성     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

---

## 2. 시스템 컴포넌트

### 2.1 Frontend (Web Client)
```
├── Meeting Preparation UI
│   ├── Markdown Editor (아젠다, 참고자료 입력)
│   ├── Participant Manager (참석자 관리)
│   └── Action Button (회의 시작)
│
├── Principles Management UI
│   ├── Principle Templates (Agile, AWS LP)
│   ├── Custom Principle Editor
│   └── Principle Selector
│
├── Meeting Room UI
│   ├── Audio Capture (맥북 마이크 입력)
│   ├── Transcript Display (실시간 자막 + 화자명)
│   ├── Agent Intervention Display (경고음 + Toast)
│   ├── Speaker Stats (발언 분포 시각화)
│   └── Meeting Controls (일시정지, 종료)
│
└── Post-Meeting UI
    ├── Meeting Summary
    ├── Action Items List
    └── Individual Feedback View
```

### 2.2 Backend Services

#### Core Services
| Service | 역할 | 기술 |
|---------|------|------|
| **API Server** | REST API 제공 | FastAPI (필요시) |
| **WebSocket Server** | 실시간 양방향 통신 | FastAPI WebSocket |
| **File Storage** | 회의 데이터 저장 | 로컬 파일시스템 (.md) |

#### AI Services
| Service | 역할 | 기술 |
|---------|------|------|
| **Realtime STT** | 실시간 음성 → 텍스트 | **OpenAI Realtime API** |
| **Speaker Diarization** | 화자 분리 | **GPT-5.2** (참석자 목록 + 컨텍스트) |
| **Agent Orchestrator** | Multi-Agent 조율 | OpenAI Agents SDK |

### 2.3 Agent 상세 설계

#### Orchestrator Agent
```python
# 역할: 전체 워크플로우 조율
responsibilities:
  - 회의 상태 전환 관리 (준비 → 진행 → 종료)
  - 적절한 Sub-Agent 호출
  - Agent 간 컨텍스트 공유
  - 최종 의사결정

tools:
  - meeting_state_manager
  - agent_dispatcher
  - file_storage
```

#### Prep Agent
```python
# 역할: 회의 전 준비 지원
responsibilities:
  - 회의 준비 자료 검증
  - 회의 원칙 로드 및 적용
  - 참석자 목록 관리

tools:
  - document_validator
  - principle_loader
  - participant_manager

triggers:
  - 회의 준비 자료 저장 시
```

#### Moderator Agent (Core)
```python
# 역할: 실시간 회의 진행 지원
responsibilities:
  - 발화 내용 실시간 분석
  - 화자 자동 분리 (참석자 목록 기반)
  - 개입 필요성 판단
  - 개입 메시지 생성 (경고음 + Toast)
  - 발언 분포 모니터링

tools:
  - transcript_analyzer
  - speaker_identifier
  - topic_tracker
  - principle_checker
  - intervention_generator

intervention_types:
  - TOPIC_DRIFT: 주제 이탈 시 복귀 유도
  - PRINCIPLE_VIOLATION: 회의 원칙 위반 지적 (LLM 판단)
  - PARTICIPATION_IMBALANCE: 발언 불균형 시 참여 독려
  - DECISION_STYLE: Top-down 감지 시 의견 요청

intervention_timing:
  - 발화자가 말을 멈췄을 때 (적극적 개입)
  - 경고음 + Toast 메시지 동시 출력
```

#### Review Agent
```python
# 역할: 회의 후 정리 및 피드백
responsibilities:
  - 회의 내용 요약
  - Action Item 추출
  - 개인별 피드백 생성
  - Markdown 파일 저장

tools:
  - summary_generator
  - action_item_extractor
  - feedback_generator
  - markdown_writer

output_files:
  - summary.md
  - action-items.md
  - transcript.md
  - interventions.md

triggers:
  - 회의 종료 시점
```

---

## 3. 데이터 모델

### 3.1 Meeting
```typescript
interface Meeting {
  id: string;
  title: string;
  status: 'preparing' | 'in_progress' | 'completed';

  // 준비 단계
  agenda: string;           // Markdown
  referenceLinks: string[];
  participants: Participant[];
  principles: Principle[];  // 적용할 회의 원칙

  // 진행 단계
  startedAt?: Date;
  transcript: TranscriptEntry[];
  interventions: Intervention[];

  // 종료 단계
  endedAt?: Date;
  summary?: string;
  actionItems: ActionItem[];
}
```

### 3.2 Participant
```typescript
interface Participant {
  id: string;
  name: string;
  role: string;             // 직책/역할

  // 회의 중 추적
  speakingTime: number;      // 초 단위
  speakingCount: number;     // 발언 횟수

  // 회의 후 피드백
  feedback?: IndividualFeedback;
}
```

### 3.3 Principle
```typescript
interface Principle {
  id: string;
  name: string;             // e.g., "수평적 의사결정"
  description: string;      // 상세 설명
  category: 'agile' | 'aws_lp' | 'custom';
  enabled: boolean;
}
```

### 3.4 TranscriptEntry
```typescript
interface TranscriptEntry {
  id: string;
  timestamp: Date;
  speaker: string;          // 화자명 (AI 자동 분리)
  text: string;
  confidence: number;       // 화자 분리 신뢰도
}
```

### 3.5 Intervention
```typescript
interface Intervention {
  id: string;
  timestamp: Date;
  type: 'TOPIC_DRIFT' | 'PRINCIPLE_VIOLATION' | 'PARTICIPATION_IMBALANCE' | 'DECISION_STYLE';
  triggerContext: string;    // 개입을 유발한 발화
  violatedPrinciple?: string; // 위반된 원칙 (해당 시)
  message: string;           // Agent가 생성한 개입 메시지
  acknowledged: boolean;     // 사용자 확인 여부
}
```

### 3.6 ActionItem
```typescript
interface ActionItem {
  id: string;
  description: string;
  assignee: string;          // 담당자 이름
  dueDate?: string;
  status: 'pending' | 'in_progress' | 'completed';
  context: string;           // 해당 Action Item이 나온 회의 맥락
}
```

---

## 4. 기술 스택

### 4.1 확정 스택

| Layer | Technology | 선택 이유 |
|-------|------------|----------|
| **Frontend** | Next.js 14 + React | 빠른 개발, App Router |
| **UI Components** | shadcn/ui + Tailwind | 빠른 UI 구성 |
| **Markdown Editor** | Monaco Editor / @uiw/react-md-editor | 풍부한 기능 |
| **Backend** | Python 3.12 | OpenAI Agents SDK 필수 |
| **Web Server** | FastAPI (필요시) | WebSocket 지원 |
| **AI/Agent** | OpenAI Agents SDK | 해커톤 주제 fit |
| **STT** | **OpenAI Realtime API** | 실시간, 저지연, 한국어 지원 |
| **LLM** | **GPT-5.2** | Agent 추론, 화자 분리, 원칙 위반 감지 |
| **Storage** | 로컬 파일시스템 (.md) | 단순, 가독성 |
| **Alert Sound** | 짧은 차임벨 (1초 이내) | 주의 환기, 비침습적 |

### 4.2 OpenAI API 활용

```python
# 사용할 OpenAI 서비스
apis:
  - Realtime API: 실시간 STT (WebSocket 기반, 저지연, 한국어)
  - GPT-5.2: Agent 추론, 원칙 위반 감지, 화자 분리
  - Agents SDK: Multi-Agent 오케스트레이션
```

---

## 5. 실시간 처리 파이프라인

```
┌──────────┐    ┌──────────────────┐    ┌──────────────┐    ┌──────────────┐
│  맥북    │ -> │ OpenAI Realtime  │ -> │   실시간     │ -> │  Transcript  │
│ 마이크   │    │ API (WebSocket)  │    │   STT 응답   │    │   + 화자분리  │
└──────────┘    └──────────────────┘    └──────────────┘    └──────────────┘
                                                            │
                                                            ▼
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────────┐
│  경고음  │ <- │  Toast   │ <- │  Moderator   │ <- │   Analysis   │
│  재생   │    │  표시    │    │    Agent     │    │  (발화 종료 시) │
└──────────┘    └──────────┘    └──────────────┘    └──────────────┘
```

### 5.1 처리 주기
- **STT**: 실시간 (streaming)
- **화자 분리**: 발화 단위
- **분석 & 개입 판단**: 발화 종료 감지 시 (침묵 1-2초)
- **발언 통계**: 실시간 업데이트
- **개입 실행**: 즉시 (경고음 + Toast)

### 5.2 개입 타이밍 상세
```
발화 중 ──────────────────────┐
                              │ 침묵 감지 (1-2초)
                              ▼
                      ┌───────────────┐
                      │ Agent 분석    │
                      │ - 주제 이탈?   │
                      │ - 원칙 위반?   │
                      │ - 참여 불균형? │
                      └───────┬───────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
     개입 필요 없음                         개입 필요
            │                                   │
            ▼                                   ▼
      다음 발화 대기                    경고음 + Toast 출력
                                       (적극적으로 개입!)
```

---

## 6. 파일 저장 구조

```
meetings/
├── 2026-01-20-sprint-review/
│   ├── preparation.md       # 회의 준비 자료
│   ├── principles.md        # 적용된 회의 원칙
│   ├── transcript.md        # 실시간 녹취록 (화자 포함)
│   ├── interventions.md     # Agent 개입 기록
│   ├── summary.md           # 회의 요약
│   └── action-items.md      # Action Items
│
└── principles/              # 회의 원칙 템플릿
    ├── agile.md
    └── aws-leadership.md
```

### 6.1 파일 포맷 예시

**transcript.md**
```markdown
# 회의 녹취록

회의: 주간 스프린트 리뷰
일시: 2026-01-20 14:00

---

[14:00:12] **김철수**: 지난 스프린트에서 8개 태스크를 완료했습니다.

[14:00:30] **이민수**: 네, 성과가 좋았어요.

[14:00:45] **이민수**: 그런데 점심 뭐 먹을까요?

> 🤖 [INTERVENTION - TOPIC_DRIFT]
> "현재 주제로 돌아갈까요? '점심 메뉴'는 Parking Lot에 추가했습니다."

[14:01:10] **김철수**: 아, 네. 다음 스프린트 계획을 보면...
```

**action-items.md**
```markdown
# Action Items

회의: 주간 스프린트 리뷰
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
```

---

## 7. 해커톤 구현 우선순위

### Phase 1: 기본 셋업 (1시간)
1. 프로젝트 구조 셋업
2. Next.js + shadcn UI 기본 화면
3. Python + OpenAI Agents SDK 연결

### Phase 2: 핵심 파이프라인 (3시간)
1. 마이크 오디오 캡처 (Web Audio API)
2. WebSocket 연결
3. OpenAI Realtime API 연동
4. AI 화자 분리 (참석자 목록 기반)
5. Moderator Agent 기본 로직
   - 주제 이탈 감지
   - 원칙 위반 감지 (LLM 판단)
6. 경고음 + Toast 개입 출력

### Phase 3: 기능 확장 (2시간)
1. 발언 분포 모니터링 & 시각화
2. 회의 원칙 편집 페이지
3. 회의록 Markdown 저장

### Phase 4: 마무리 (1시간)
1. 회의 종료 → 리캡 생성
2. Action Item 추출
3. 데모 리허설

---

## 8. 폴더 구조 (권장)

```
meetingmod/
├── frontend/                 # Next.js 앱
│   ├── app/
│   │   ├── page.tsx         # 메인 (회의 준비)
│   │   ├── principles/
│   │   │   └── page.tsx     # 회의 원칙 관리
│   │   ├── meeting/
│   │   │   └── [id]/
│   │   │       └── page.tsx # 회의 진행 화면
│   │   └── review/
│   │       └── [id]/
│   │           └── page.tsx # 회의 결과 화면
│   ├── components/
│   │   ├── markdown-editor.tsx
│   │   ├── principle-editor.tsx
│   │   ├── meeting-room.tsx
│   │   ├── transcript-view.tsx
│   │   ├── intervention-toast.tsx
│   │   ├── alert-sound.tsx
│   │   └── speaker-stats.tsx
│   └── lib/
│       ├── websocket.ts
│       ├── audio-capture.ts
│       └── sound-player.ts
│
├── backend/                  # Python
│   ├── main.py              # 엔트리포인트
│   ├── server.py            # FastAPI (필요시)
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── prep_agent.py
│   │   ├── moderator_agent.py
│   │   └── review_agent.py
│   ├── services/
│   │   ├── stt_service.py
│   │   ├── speaker_service.py
│   │   └── storage_service.py
│   └── models/
│       └── meeting.py
│
├── meetings/                 # 회의 데이터 저장
│   └── {meeting-id}/
│       ├── preparation.md
│       ├── transcript.md
│       └── ...
│
└── principles/               # 회의 원칙 템플릿
    ├── agile.md
    └── aws-leadership.md
```
