# 개발자 가이드

[English](DEVELOPER-GUIDE.en.md) | 한국어

이 문서는 MeetingMod 프로젝트의 기술적인 상세 내용을 다룹니다.

## 목차

- [프로젝트 구조](#프로젝트-구조)
- [환경 설정](#환경-설정)
- [백엔드](#백엔드)
- [프론트엔드](#프론트엔드)
- [Multi-Agent 시스템](#multi-agent-시스템)
- [LLM 출력 검증](#llm-출력-검증)
- [데이터 모델](#데이터-모델)
- [실시간 파이프라인](#실시간-파이프라인)
- [관련 문서](#관련-문서)

## 프로젝트 구조

```
GradientHair/
├── frontend/                 # Next.js 앱
│   ├── app/                  # App Router 페이지
│   ├── components/           # React 컴포넌트
│   └── lib/                  # 유틸리티
│
├── backend/                  # Python 서버
│   ├── server.py             # FastAPI 메인 서버
│   ├── agents/               # Multi-Agent 구현
│   ├── services/             # 비즈니스 로직
│   └── models/               # 데이터 모델
│
├── docker/                   # Docker 설정
│   └── docker-compose.yml
│
├── meetings/                 # 회의 데이터 저장
│   └── {meeting-id}/
│       ├── preparation.md
│       ├── transcript.md
│       ├── interventions.md
│       ├── summary.md
│       └── action-items.md
│
├── principles/               # 회의 원칙 템플릿
│   ├── agile.md
│   └── aws-leadership.md
│
└── docs/                     # 문서
```

## 환경 설정

### 필수 요구사항

- Node.js 18+
- Python 3.12+
- OpenAI API Key
- Docker (데모 실행 시)

### Backend 설정

```bash
# 환경 변수 파일 생성
make env-backend

# backend/.env 수정
OPENAI_API_KEY=your_key_here
CORS_ORIGINS=http://localhost:3000
```

### Frontend 설정

```bash
# 환경 변수 파일 생성
make env-frontend

# frontend/.env.local (자동 생성됨)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### 실행 방법

```bash
# Docker로 실행 (권장)
docker compose --env-file backend/.env -f docker/docker-compose.yml up -d --build

# 또는 로컬 개발 모드
make run-local-dev

# 개별 실행
make run-backend   # Backend만
make run-frontend  # Frontend만
```

## 백엔드

### 기술 스택

| 기술 | 용도 |
|------|------|
| FastAPI | REST API, WebSocket 서버 |
| OpenAI Realtime API | 실시간 음성 인식 (STT) |
| OpenAI Agents SDK | Multi-Agent 오케스트레이션 |
| OpenAI SDK | LLM 호출 (GPT-4) |

### 주요 서비스

- `server.py` - FastAPI 메인 서버 (REST + WebSocket)
- `services/` - STT, 화자 분리, 스토리지 서비스
- `agents/` - Multi-Agent 구현

## 프론트엔드

### 기술 스택

| 기술 | 용도 |
|------|------|
| Next.js | React 프레임워크 |
| React | UI 라이브러리 |
| Tailwind CSS | 스타일링 |
| shadcn/ui | UI 컴포넌트 |
| Zustand | 상태 관리 |

### 주요 페이지

- `/` - 회의 준비 페이지 (아젠다, 참석자 입력)
- `/meeting/{id}` - 회의 진행 페이지 (실시간 자막, 개입 알림)
- `/review/{id}` - 회의 결과 페이지 (요약, Action Items)

## Multi-Agent 시스템

### Agent 구성

```
               Triage Agent (Intent 분류 / Handoff)
              /       |        \
         Topic    Principle  Participation
         Agent       Agent       Agent
              \       |        /
                Intervention Merge
```

| Agent | 역할 |
|-------|------|
| Triage Agent | 발화 의도 분류, 적절한 Agent로 핸드오프 |
| Topic Agent | 주제 이탈 감지 및 복귀 유도 |
| Principle Agent | 회의 원칙 위반 감지 및 지적 |
| Participation Agent | 발언 불균형 감지 및 참여 독려 |
| Review Agent | 회의 후 요약, Action Item, 피드백 생성 |

### 개입 유형

- `TOPIC_DRIFT` - 주제 이탈 시 복귀 유도
- `PRINCIPLE_VIOLATION` - 회의 원칙 위반 지적
- `PARTICIPATION_IMBALANCE` - 발언 불균형 시 참여 독려

## LLM 출력 검증

LLM 출력 정합성을 3단계로 보강:

1. **Pydantic 스키마 파싱** + structured output(JSON) 강제
2. **에러 피드백 재시도** - 실패 시 에러 메시지를 포함한 재시도 루프
3. **선택적 DSPy 검증** - `DSPY_VALIDATE=1`로 추가 안전장치

관련 문서: [PR #5](https://github.com/GradientHair/GradientHair/pull/5)

### 비용/지연 최적화

- **모델 라우터**: 작은 작업은 빠른 모델, 복잡한 작업은 고성능 모델
- **Diarize 후처리**: 실시간 STT는 Realtime API, 화자 분리는 회의 종료 후 배치 처리

## 데이터 모델

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

### 파일 저장 구조

```
meetings/{meeting-id}/
├── preparation.md       # 회의 준비 자료
├── principles.md        # 적용된 회의 원칙
├── transcript.md        # 실시간 녹취록
├── interventions.md     # Agent 개입 기록
├── summary.md           # 회의 요약
├── action-items.md      # Action Items
└── transcript_diarized.md  # 화자 분리된 녹취록 (후처리)
```

## 실시간 파이프라인

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

### 처리 주기

- **STT**: 실시간 (streaming)
- **개입 판단**: 발화 종료 감지 시
- **개입 실행**: 즉시 (경고음 + Toast)
- **화자 분리**: 회의 종료 후 배치 처리

## 관련 문서

- [요구사항](00-REQUIREMENTS.md)
- [PRD](01-PRD.md)
- [아키텍처](02-ARCHITECTURE.md)
- [유저 플로우](03-USER-FLOW.md)
- [API 스펙](04-API-SPEC.md)
- [데모 시나리오](05-DEMO-SCENARIO.md)
- [구현 가이드](06-IMPLEMENTATION-GUIDE.md)
- [Multi-Agent 설계](07-MULTI-AGENT-DESIGN.md)
