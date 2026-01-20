# GradientHair

Multi-Agent 개발을 위한 Skills 레포지토리입니다. Codex CLI의 multi-agent workflow 활용 가이드를 제공합니다.

## 문제 정의

기업 환경에서 Multi-Agent 작업은 반복적인 운영 비용과 품질 편차를 동반합니다. 이 레포는 복잡한 작업을
안전하게 분해하고 병렬로 수행할 수 있는 표준화된 스킬을 제공해, 개발 생산성과 운영 일관성을 높이는 것을
목표로 합니다.

정량 KPI 예시(조직 상황에 따라 달라질 수 있는 목표 지표):
- 작업 분해/핸드오프에 소요되는 리드타임 30~50% 단축 목표
- 리뷰/검증 사이클 소요 시간 25~40% 절감 목표
- 모델 라우팅 최적화로 평균 LLM 비용 30~60% 절감 목표

## 설치 방법

### 1. 레포지토리 클론

```bash
git clone https://github.com/GradientHair/GradientHair ~/.codex/skills/GradientHair
# 또는
#
git clone https://github.com/GradientHair/GradientHair ~/.claude/skills/GradientHair
```

### 2. Codex/Claude Code에서 사용

클론 후 자동으로 skill이 인식됩니다.

## 포함된 Skills

### multi-agent-guide

Codex CLI의 Multi-Agent Workflow 구현 가이드입니다. Orchestrator-Worker 패턴을 사용한 복잡한 작업 분해 및
병렬 처리를 다룹니다.

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

복잡한 작업에서 파일 기반 플래닝을 수행하는 워크플로우입니다. task_plan.md, findings.md, progress.md 패턴과
세션 복구 스크립트를 제공합니다.

**주요 내용:**
- planning-with-files 패턴 및 템플릿
- 세션 복구/검증 스크립트
- 예시와 레퍼런스 문서

### openai-agents-python

OpenAI Agents Python 사용 예제와 스킬 가이드입니다.

**주요 내용:**
- 예제 및 활용 가이드
- 스킬 문서

## 팀

- 김동현: STT 개발
- 신훈철: 팀장/기획, Agent 개발
- 전종섭: App 개발
- 김재연: Agent 개발

## AGENTS.md

프로젝트 수준의 에이전트 설정 파일입니다. 복잡한 작업에 대한 multi-agent workflow 가이드를 제공합니다.

## 참고 자료

- [Codex CLI GitHub](https://github.com/openai/codex)

## English README

- `README.en.md`
