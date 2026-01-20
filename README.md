# GradientHair

> 실시간 회의 개입과 회의 후 피드백을 제공하는 멀티에이전트 회의 운영 데모

OpenAI Coxwave Hackathon 요구사항에 맞춰, 회의 도중의 **주제 이탈/원칙 위반/참여 불균형**을
실시간으로 감지하고 개입하는 AI Meeting Moderator를 구현합니다.

## 데모

- 데모 URL: [https://drive.google.com/file/d/1sPHJUzlK99Yc9_ltLSoejJ2X769t9jgz/view?usp=sharing](https://drive.google.com/file/d/1sPHJUzlK99Yc9_ltLSoejJ2X769t9jgz/view?usp=sharing)
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

## 문서

- [개발자 가이드](docs/DEVELOPER-GUIDE.ko.md)
- [English README](README.en.md)
