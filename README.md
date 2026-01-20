# GradientHair

> 실시간 회의 개입과 회의 후 피드백을 제공하는 멀티에이전트 회의 운영 데모

OpenAI Coxwave Hackathon 요구사항에 맞춰, 회의 도중의 **주제 이탈/원칙 위반/참여 불균형**을
실시간으로 감지하고 개입하는 AI Meeting Moderator를 구현합니다.

## 데모

- 데모 URL: (추가 예정)
- 데모 영상: (추가 예정)

### 데모 플로우 (로컬)
1. `http://localhost:3000` 접속
2. 회의 제목/참석자/아젠다 입력
3. **회의 시작** → `/meeting/{id}` 진입
4. **에이전트 모드**에서 실시간 자막/개입 확인
5. **회의 종료** → `/review/{id}` 이동 및 파일 저장 확인

## 문제 정의

회의 중 주제 이탈, 원칙 위반, 참여 불균형을 **실시간으로 감지·개입**하고,
회의 종료 후에는 **요약/액션 아이템/개인 피드백**을 자동 생성해야 한다.

## 솔루션

Realtime STT → 발화/상태 업데이트 → 멀티에이전트 분석 → 개입(토스트/알림) 흐름으로
회의 중 개입을 수행하고, 회의 종료 시 Review Agent가 요약/액션 아이템/피드백을 생성하여
Markdown으로 저장한다.

## 조건 충족 여부

- [x] OpenAI API 사용
- [x] 멀티에이전트 구현
- [x] 실행 가능한 데모

## 핵심 기능

- 실시간 음성 인식 (OpenAI Realtime API)
- 참석자 기반 화자 분리
- 주제 이탈/원칙 위반/참여 불균형 감지 및 개입
- 회의 요약/액션 아이템/피드백 Markdown 저장

## 아키텍처

```
Audio -> Realtime STT -> Meeting State Store
                    |
                    v
                Triage Agent
          (Intent 분류 / Handoff)
        /        |        \
   Topic Agent  Principle  Participation
        \        |        /
           Intervention Merge
                 |
            Alert + Toast

Post-meeting:
  Review Agent -> summary/action-items/feedback.md
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

## 예시 회의 (샘플)

**회의명:** 챗봇 화면 기획 논의  
**일시:** 1월 20일 (화요일) ⋅ AM 10:00 ~ 10:30  
**참석자:** 2명 (초대 수락 1명, 회신 대기 1명)

**참석자 정보**
- Jongseob Jeon (Aiden) — 주최자, hunhoon21@gmail.com

**아젠다**
안녕하세요 훈철님  
이전에 comm 한 것 처럼 개발 환경 초안에 대해서 논의하는 미팅입니다.

**회의 메모**
- Jongseob Jeon: 한가함

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

| 이름 | 역할 |
| ---- | ---- |
|      |      |
|      |      |
|      |      |
