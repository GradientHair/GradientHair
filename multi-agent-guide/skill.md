---
name: multi-agent-guide
description: Multi-agent workflow 구현 가이드. Orchestrator-Worker 패턴으로 복잡한 작업 분해 및 병렬 처리. spawn_agent, send_input, wait, close_agent 도구 사용법 포함. 대규모 작업, 코드 리뷰, 테스트 실행 시 활용.
---

# Multi-Agent Workflow Guide

This guide explains how to use multi-agent workflows in Codex for handling complex tasks through the Orchestrator-Worker pattern.

## 1. Orchestrator-Worker Pattern Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Orchestrator                          │
│  - Decomposes tasks and delegates to workers                 │
│  - Performs only lightweight tasks directly                  │
│  - Monitors via wait(), verifies completion                  │
└─────────────────┬───────────────────────────────────────────┘
                  │ spawn_agent() / send_input() / wait()
    ┌─────────────┼─────────────┬─────────────────┐
    ▼             ▼             ▼                 ▼
┌─────────┐ ┌─────────┐ ┌─────────┐         ┌─────────┐
│ Worker1 │ │ Worker2 │ │ Worker3 │   ...   │ WorkerN │
└─────────┘ └─────────┘ └─────────┘         └─────────┘
                        │
              Shared Environment (filesystem, state)
```

### Agent Roles

| Role | Description | Use Case |
|------|-------------|----------|
| `orchestrator` | Task decomposition and coordination only | Complex multi-step tasks |
| `worker` | Actual task execution | Individual subtasks |
| `default` | Inherits parent settings | General purpose |

## 2. Collab Tools Quick Reference

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `spawn_agent` | Create new agent | `message`, `agent_type` |
| `send_input` | Send message to agent | `id`, `message`, `interrupt` |
| `wait` | Monitor agent(s) | `ids`, `timeout_ms` |
| `close_agent` | Terminate agent | `id` |

**See**: `references/collab-tools.md` for detailed API documentation.

## 3. Core Best Practices

### Orchestrator Principles

1. **Never stop monitoring** - Continue watching while workers are active
2. **Be patient** - Don't rush workers
3. **Never return until fully complete** - Verify all work before responding

### Workflow Pattern

```
1. Analyze request → Determine optimal worker configuration
2. Spawn workers (clear goals, constraints, expected outputs)
3. Monitor with wait()
4. On worker completion:
   - Verify accuracy
   - Check integration with other tasks
   - Evaluate overall progress
5. If issues found → Assign fixes to appropriate worker → Repeat 3-5
6. close_agent() when no longer needed
7. Return to user only when fully complete and verified
```

### Critical Rules

- **Monitor only via `wait()`** - No status check messages
- **Workers are autonomous** - They can execute commands, modify/create/delete files
- **Shared environment** - Inform workers they share the same workspace
- **Avoid conflicts** - Workers must not overwrite each other's work
- **No infinite recursion** - Workers cannot spawn sub-agents by default

**See**: `references/best-practices.md` for detailed guidelines.

## 4. When to Use Multi-Agent

### Good Use Cases
- Large tasks with multiple well-defined scopes
- Code review by another agent
- Idea discussion (fresh context for insights)
- Test execution and fixes (context optimization)
- Log-heavy operations (context preservation)

### Avoid When
- Simple or straightforward tasks
- Small scope modifications
- Tasks that don't benefit from parallelization

**See**: `references/patterns.md` for usage patterns and examples.

## 5. References

For detailed information, see the reference files in this skill:

- **`references/best-practices.md`** - Comprehensive best practices guide
- **`references/collab-tools.md`** - Complete Collab Tools API reference
- **`references/patterns.md`** - Usage patterns with concrete examples
