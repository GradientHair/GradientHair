# GradientHair

> 실시간 회의 개입과 회의 후 피드백을 제공하는 멀티에이전트 회의 운영 데모

## 데모

Quick start:
```bash
cp docker/.env.compose.example .env.compose
# edit .env.compose and set OPENAI_API_KEY
docker compose -f docker/docker-compose.yml --env-file .env.compose up --build
(데모 URL 또는 영상 링크)

## 문제 정의

회의 중 주제 이탈, 원칙 위반, 참여 불균형을 실시간으로 감지·개입하고,
회의 종료 후에는 요약/액션 아이템/개인 피드백을 자동으로 제공해야 한다.

## 솔루션

STT → 발화/상태 업데이트 → 멀티에이전트 분석 → 개입(토스트/알림) 흐름으로 회의 중 개입을 수행하고,
회의 종료 시 Review Agent가 요약/액션 아이템/개인 피드백을 생성하여 Markdown으로 저장한다.

## 조건 충족 여부

- [x] OpenAI API 사용
- [x] 멀티에이전트 구현
- [x] 실행 가능한 데모

## 아키텍처

```
Audio/STT -> Meeting State Store
                 |
                 v
           Safety Orchestrator
      (Planner/Verifier/Adversarial)
        /        |        \
   Topic Agent  Principle  Participation
        \        |        /
           Intervention Merge
                 |
            UI Toast + Alert

Post-meeting:
  Review Agent -> summary/action-items/feedback.md
```

## 설치 방법
- Python 3.12, FastAPI
- OpenAI SDK, Realtime API
- Next.js + React

## 설치 및 실행

```bash
# from repo root
docker compose -f docker/docker-compose.yml --env-file .env.compose down
docker compose -f docker/docker-compose.yml --env-file .env.compose up --build -d
```


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

## 향후 계획 (Optional)

- 실시간 Realtime API 기반 음성 파이프라인 고도화
- 모델/정책별 평가(Eval) 자동화

## 팀원

| 이름 | 역할 |
| ---- | ---- |
|      |      |
|      |      |
|      |      |
