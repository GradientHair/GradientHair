# GradientHair

A skills repository for Multi-Agent development, providing guidance for Codex CLI multi-agent workflows.

## Problem Statement

In enterprise settings, multi-agent work often incurs recurring operational cost and quality variance. This repo
provides standardized skills to safely decompose and parallelize complex work, improving developer productivity and
operational consistency.

Quantitative KPI examples (target metrics that may vary by organization):
- 30-50% reduction in lead time for decomposition and handoffs
- 25-40% reduction in review/validation cycle time
- 30-60% reduction in average LLM cost via model routing optimization

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/GradientHair/GradientHair ~/.codex/skills/GradientHair
# or
#
git clone https://github.com/GradientHair/GradientHair ~/.claude/skills/GradientHair
```

### 2. Use in Codex/Claude Code

After cloning, the skills are discovered automatically.

## Included Skills

### multi-agent-guide

Guide for implementing Multi-Agent workflows in Codex CLI. Covers decomposition and parallelization via the
Orchestrator-Worker pattern.

**File layout:**
- `SKILL.md` / `skill.md` - Orchestrator-Worker overview and Collab Tools quick reference
- `references/best-practices.md` - Detailed best practices
- `references/collab-tools.md` - spawn_agent, send_input, wait, close_agent API reference
- `references/patterns.md` - Six usage patterns and examples

**Highlights:**
- Orchestrator-Worker pattern architecture
- Collab Tools (spawn_agent, send_input, wait, close_agent)
- Parallelization, code review, TDD, and large refactor patterns
- Anti-patterns and usage guidance

### planning-with-files

A file-driven planning workflow for complex tasks. Provides task_plan.md, findings.md, progress.md patterns and
session recovery scripts.

**Highlights:**
- planning-with-files patterns and templates
- session recovery and validation scripts
- examples and reference documents

### openai-agents-python

Examples and guides for OpenAI Agents in Python.

**Highlights:**
- examples and usage guides
- skill documentation

## Team

- Donghyun Kim: STT development
- Huncheol Shin: Team lead/planning, Agent development
- Jongseob Jeon: App development
- Jaeyeon Kim: Agent development

## AGENTS.md

Project-level agent configuration file with guidance for complex multi-agent workflows.

## References

- [Codex CLI GitHub](https://github.com/openai/codex)
