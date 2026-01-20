# Agent Guidelines

이 레포지토리의 skills를 활용하기 위한 에이전트 가이드라인입니다.

## Multi-Agent Workflow

<IMPORTANT>
복잡한 작업(3개 이상의 독립적인 하위 작업)에는 multi-agent workflow를 고려하세요:

1. **multi-agent-guide skill 참조**: `multi-agent-guide/skill.md` 읽기
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

## Planning with Files

<IMPORTANT>
복잡한 작업 (3+ 단계, 리서치, 프로젝트)에는:

1. **planning-with-files skill 참조** (설치되어 있다면)
2. 프로젝트 디렉토리에 다음 파일 생성:
   - `task_plan.md` - 작업 계획
   - `findings.md` - 조사 결과
   - `progress.md` - 진행 상황
3. 작업 전반에 걸쳐 3-file 패턴 유지
</IMPORTANT>

## Quick Reference

| 상황 | 권장 접근 |
|------|----------|
| Codex CLI에서 복잡한 작업 | multi-agent-guide 참조 → Orchestrator-Worker 패턴 |
| 리서치/계획이 필요한 작업 | planning-with-files 패턴 |
| 단순한 단일 작업 | 직접 수행 (multi-agent 불필요) |
