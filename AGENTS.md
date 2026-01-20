# Agent Guidelines

이 레포지토리의 skills를 활용하기 위한 에이전트 가이드라인입니다.

## Multi-Agent Workflow

<IMPORTANT>
복잡한 작업(3개 이상의 독립적인 하위 작업)에는 multi-agent workflow를 고려하세요:

1. **multi-agent-guide skill 참조**: `skills/multi-agent-guide/skill.md` 읽기
2. **Orchestrator-Worker 패턴 적용**:
   - Orchestrator: 작업 분해, 위임, 모니터링
   - Worker: 실제 작업 수행 (spawn_agent로 생성)
3. **Collab Tools 사용**: spawn_agent, send_input, wait, close_agent

적합한 경우:
- 여러 독립적인 범위를 가진 대규모 작업
- 코드 리뷰 (fresh context)
- 테스트 실행 및 수정
- 로그가 많이 발생하는 작업

피해야 할 경우:
- 단순하거나 직관적인 작업
- 작은 범위의 수정
</IMPORTANT>

## Quick Reference

| 상황 | 권장 접근 |
|------|----------|
| Codex CLI에서 복잡한 작업 | multi-agent-guide 참조 → Orchestrator-Worker 패턴 |
| 단순한 단일 작업 | 직접 수행 (multi-agent 불필요) |

## Required Workflow (Always)

1. 개발 완료 후, 동작 테스트를 먼저 수행한다.  
   - `scripts/run_smoke.sh` 실행 → `.last_test_run` 갱신
2. 커밋은 에이전트가 직접 수행한다. (사람은 수행하지 않음)
3. 커밋 직후, `review-agent-safety` 기준을 자동 검사한다.  
   - `scripts/review_agent_safety_check.py` 실행 (score 출력 확인)

- 훅 템플릿 설치: `scripts/install_hooks.sh` 실행

이 워크플로우는 git hook으로 강제된다:
- `pre-commit`: 최근 테스트 스탬프 확인
- `post-commit`: review-agent-safety 기준 검사

## Playwright UI Demo Flow (Shareable)

다른 사람이 동일하게 재현 가능한 UI 데모 플로우입니다.

### 사전 준비
1. 백엔드/프론트 모두 실행
2. 프론트 환경 변수 설정(로컬):
   - `frontend/.env.local`
     - `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`
     - `NEXT_PUBLIC_WS_URL=ws://localhost:8000`

### 실행 순서 (Playwright 또는 수동)
1. `http://localhost:3000` 접속
2. 회의 제목 입력 → 참석자(이름/역할) 추가 → 아젠다 입력
3. **회의 시작** 클릭 → `/meeting/{id}` 진입 확인
4. **데모 모드** 클릭 → 실시간 자막 출력 확인
5. 개입 메시지 확인:
   - `TOPIC_DRIFT`
   - `PRINCIPLE_VIOLATION`
6. 개입 카드 **확인** 클릭(오버레이 제거)
7. **회의 종료** 클릭 → `/review/{id}` 이동 확인
8. 저장 파일 목록 확인:
   - `summary.md`
   - `action-items.md`
   - `interventions.md`
   - `transcript.md`

### 확인 포인트
- `/meeting/{id}`에서 상태가 “연결됨”으로 표시되는지
- 데모 모드에서 자막/개입이 생성되는지
- 리뷰 화면에서 저장 경로가 표시되는지
