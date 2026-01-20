# GradientHair

> 실시간 회의 개입과 회의 후 피드백을 제공하는 멀티에이전트 회의 운영 데모

OpenAI Coxwave Hackathon 요구사항에 맞춰, 회의 도중의 **주제 이탈/원칙 위반/참여 불균형**을
실시간으로 감지하고 개입하는 AI Meeting Moderator를 구현합니다.

## 데모

- 데모 URL: (추가 예정)
- 데모 영상: assets/demo.mov

### 데모 실행
1. `backend/.env` 파일 생성 및 API key 기입
```
OPENAI_API_KEY=<YOUR_API_KEY>
```
2. docker compose up 실행
```bash
docker compose --env-file backend/.env -f docker/docker-compose.yml up -d --build
```
3. 데모 이후 자원 정리
```bash
docker compose --env-file backend/.env -f docker/docker-compose.yml down
```

### 데모 플로우 (로컬)
1. `http://localhost:3000` 접속

2. 회의 제목/참석자/아젠다 입력
     
     <img src="./assets/google_cal_invi.png" alt="예시" width="300"/>
     
     ```plaintext
     챗봇 화면 기획 논의
     1월 20일 (화요일)⋅AM 10:00~ 10:30
     참석자 2명
     초대 수락 1명, 회신 대기 중 1명
     Jongseob Jeon (Aiden)
     주최자
     hunhoon21@gmail.com
     안녕하세요 훈철님
     이전에 comm 한 것 처럼 개발 환경 초안에 대해서 논의하는 미팅입니다.
     Jongseob Jeon
     한가함
     ```

3. **회의 시작** → `/meeting/{id}` 진입
4. **에이전트 모드**에서 실시간 자막/개입 확인
5. **회의 종료** → `/review/{id}` 이동 및 파일 저장 확인

## 문제 정의

회의 중 주제 이탈, 원칙 위반, 참여 불균형을 **실시간으로 감지·개입**하고,
회의 종료 후에는 **요약/액션 아이템/개인 피드백**을 자동 생성해야 한다.

## 솔루션

Realtime STT로 발화를 수집해 Meeting State를 갱신하고, 멀티에이전트가 실시간 개입을 수행한다.
회의 종료 후에는 Review Agent가 요약/액션 아이템/피드백을 생성해 Markdown으로 저장한다.

LLM 출력 정합성은 3단계로 보강한다(함수 호출/structured output 스타일 JSON).
1) Pydantic 스키마 파싱 + structured output(JSON) 강제
2) 실패 시 에러 메시지를 포함한 재시도 루프 (error feedback loop)
3) 선택적 DSPy 검증 단계(DSPY_VALIDATE=1)로 추가 안전장치
(관련 문서화: [PR #5](https://github.com/GradientHair/GradientHair/pull/5))

실용주의 관점에서 비용/지연을 줄이기 위해 모델 라우터를 두고,
실시간 STT는 Realtime API로 처리하되 화자 분리(diarization)는 회의 종료 후
배치(post-process)로 분리하여 비용과 지연을 분산한다.

## 조건 충족 여부

- [x] OpenAI API 사용
- [x] 멀티에이전트 구현
- [x] 실행 가능한 데모
- [x] LLM structured output 검증 파이프라인(스키마 파싱 → 에러 피드백 재시도 → DSPy 옵션)
- [x] 실용적 비용/지연 최적화(모델 라우팅, diarize 후처리 분리)

## 핵심 기능

- 실시간 음성 인식 (OpenAI Realtime API)
- 회의 종료 후 diarize 기반 화자 분리(배치 처리)
- 주제 이탈/원칙 위반/참여 불균형 감지 및 개입
- 회의 요약/액션 아이템/피드백 Markdown 저장
- LLM structured output 검증 파이프라인(Pydantic + retry + DSPy 옵션)
- Model Router 기반 비용/속도 최적화(작은 작업은 빠른 모델, 복잡한 작업은 고성능 모델)

## 아키텍처

```
Meeting (Live):
  Audio -> Realtime STT -> Meeting State Store
                      |
                      v
               Triage Agent
         (Intent 분류 / Handoff)
          /       |        \
     Topic     Principle  Participation
     Agent        Agent       Agent
          \       |        /
            Intervention Merge
                   |
              Alert + Toast

  LLM Calls:
    Model Router -> Structured Output Runner
                   (Pydantic parse + error feedback retry + optional DSPy)

Post-meeting (Async):
  Review Agent -> summary/action-items/feedback.md
  Diarize Job  -> transcript_diarized.md/.json
```

## 저장 구조

```
meetings/
└── {meeting-id}/
    ├── preparation.md
    ├── principles.md
    ├── transcript.md
    ├── interventions.md
    ├── summary.md
    └── action-items.md
```

## 기술 스택

- Backend: Python 3.12, FastAPI
- AI/Agents: OpenAI SDK, OpenAI Agents SDK
- STT: OpenAI Realtime API
- Frontend: Next.js + React + shadcn/ui

## 설치 및 실행

```bash
# 환경 설정
# (backend) OPENAI_API_KEY 설정 후 실행
make env-backend
make env-frontend

# 의존성 설치
make setup-backend
make setup-frontend

# 실행
make run-local-dev
```

## 제출 가이드 (해커톤 기준)

- GitHub Public 레포지토리
- 레포 이름 = 팀 이름
- README에 데모 링크/영상 포함
- 마감 시점의 `main` 브랜치 기준으로 심사

## 향후 계획 (Optional)

- Realtime STT 파이프라인 안정화 및 지연 최적화
- 모델/정책별 평가(Eval) 자동화

## 팀원

- 김동현: STT 개발
- 신훈철: 팀장/기획, Agent 개발
- 전종섭: App 개발
- 김재연: Agent 개발

---

# 개발자 가이드

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
make env-backend
# backend/.env 수정: OPENAI_API_KEY=your_key_here
```

### Frontend 설정

```bash
make env-frontend
# frontend/.env.local 자동 생성
```

## 백엔드 기술 스택

| 기술 | 용도 |
|------|------|
| FastAPI | REST API, WebSocket 서버 |
| OpenAI Realtime API | 실시간 음성 인식 (STT) |
| OpenAI Agents SDK | Multi-Agent 오케스트레이션 |
| OpenAI SDK | LLM 호출 (GPT-4) |

## 프론트엔드 기술 스택

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

## 데이터 모델

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

- [요구사항](docs/00-REQUIREMENTS.md)
- [PRD](docs/01-PRD.md)
- [아키텍처](docs/02-ARCHITECTURE.md)
- [유저 플로우](docs/03-USER-FLOW.md)
- [API 스펙](docs/04-API-SPEC.md)
- [데모 시나리오](docs/05-DEMO-SCENARIO.md)
- [구현 가이드](docs/06-IMPLEMENTATION-GUIDE.md)
- [Multi-Agent 설계](docs/07-MULTI-AGENT-DESIGN.md)

## English README

- [README.en.md](README.en.md)
