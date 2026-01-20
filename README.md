# GradientHair

Meeting Operator demo app (React + Python + OpenAI SDK) + Multi-Agent workflow docs.

## Demo App (Meeting Operator)

Quick start:
```bash
export OPENAI_API_KEY=sk-...
docker compose up --build
```

Open the UI at `http://localhost:3000`. Full instructions are in `docs/08-DEMO-APP.md`.

## 설치 방법

### 1. 레포지토리 클론

```bash
git clone https://github.com/GradientHair/GradientHair ~/.codex/skills/GradientHair
# 또는
git clone https://github.com/GradientHair/GradientHair ~/.claude/skills/GradientHair
```

### 2. Codex/Claude Code에서 사용

클론 후 자동으로 skill이 인식됩니다.

## 포함된 Skills

### multi-agent-guide

Codex CLI의 Multi-Agent Workflow 구현 가이드입니다. Orchestrator-Worker 패턴을 사용한 복잡한 작업 분해 및 병렬 처리를 다룹니다.

**파일 구조:**
- `SKILL.md` / `skill.md` - Orchestrator-Worker 패턴 개요, Collab Tools 빠른 참조
- `references/best-practices.md` - 상세 Best Practices
- `references/collab-tools.md` - spawn_agent, send_input, wait, close_agent API 레퍼런스
- `references/patterns.md` - 6가지 활용 패턴 및 예시

**주요 내용:**
- Orchestrator-Worker 패턴 아키텍처
- Collab Tools (spawn_agent, send_input, wait, close_agent)
- 병렬 처리, 코드 리뷰, TDD, 대규모 리팩토링 패턴
- Anti-patterns 및 사용 가이드

### planning-with-files

복잡한 작업에서 파일 기반 플래닝을 수행하는 워크플로우입니다. task_plan.md, findings.md, progress.md 패턴과 세션 복구 스크립트를 제공합니다.

**주요 내용:**
- planning-with-files 패턴 및 템플릿
- 세션 복구/검증 스크립트
- 예시와 레퍼런스 문서

### openai-agents-python

OpenAI Agents Python 사용 예제와 스킬 가이드입니다.

**주요 내용:**
- 예제 및 활용 가이드
- 스킬 문서

## AGENTS.md

프로젝트 수준의 에이전트 설정 파일입니다. 복잡한 작업에 대한 multi-agent workflow 가이드를 제공합니다.

## 참고 자료

- [Codex CLI GitHub](https://github.com/openai/codex)
