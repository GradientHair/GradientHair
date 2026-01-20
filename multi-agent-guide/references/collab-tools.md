# Collab Tools API Reference

## Overview

Collab tools enable multi-agent workflows in Codex. These four tools allow you to spawn, communicate with, monitor, and terminate worker agents.

## 1. spawn_agent

Creates a new agent to handle a task.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | Task instructions for the agent |
| `agent_type` | string | No | Agent role: `default`, `orchestrator`, or `worker` |

### Agent Types

| Type | Model | Base Instructions | Use Case |
|------|-------|-------------------|----------|
| `default` | Inherits parent | Inherits parent | General purpose |
| `orchestrator` | Inherits parent | orchestrator.md | Task coordination |
| `worker` | gpt-5.2-codex | gpt-5.2-codex_prompt.md | Task execution |

### Example

```json
{
  "message": "Implement the authentication module in /src/auth/. Create login, logout, and session management functions. Use JWT tokens. Write tests for all functions.",
  "agent_type": "worker"
}
```

### Returns

```json
{
  "agent_id": "uuid-string"
}
```

### Events

| Event | When |
|-------|------|
| `CollabAgentSpawnBeginEvent` | Spawn initiated |
| `CollabAgentSpawnEndEvent` | Agent ready |

---

## 2. send_input

Sends a message to an existing agent.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | string | Yes | - | Target agent ID |
| `message` | string | Yes | - | Message content |
| `interrupt` | boolean | No | `false` | Interrupt current work |

### Interrupt Behavior

| `interrupt` | Behavior |
|-------------|----------|
| `false` | Message queued, processed after current work completes |
| `true` | Current work interrupted, message processed immediately |

### Example - Follow-up Task

```json
{
  "id": "agent-uuid",
  "message": "Now add rate limiting to the authentication endpoints you created.",
  "interrupt": false
}
```

### Example - Redirect Work

```json
{
  "id": "agent-uuid",
  "message": "Stop current work. The requirements have changed. Now focus on OAuth2 integration instead.",
  "interrupt": true
}
```

### Events

| Event | When |
|-------|------|
| `CollabAgentInteractionBeginEvent` | Message sent |
| `CollabAgentInteractionEndEvent` | Message processed |

### Important Notes

- With `interrupt=false`, the agent won't see your message until it finishes current work
- Don't use `send_input` for status checks - use `wait()` instead
- Use `interrupt=true` sparingly and intentionally

---

## 3. wait

Monitors one or more agents for completion.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `ids` | string[] | Yes | - | Agent IDs to monitor |
| `timeout_ms` | number | No | 30000 | Timeout in milliseconds (max 300000 / 5 min) |

### Example - Single Agent

```json
{
  "ids": ["agent-uuid-1"],
  "timeout_ms": 60000
}
```

### Example - Multiple Agents

```json
{
  "ids": ["agent-uuid-1", "agent-uuid-2", "agent-uuid-3"],
  "timeout_ms": 120000
}
```

### Returns

Returns when the first agent completes or timeout is reached.

```json
{
  "completed_id": "agent-uuid-1",
  "status": "completed",
  "result": "..."
}
```

### Events

| Event | When |
|-------|------|
| `CollabWaitingBeginEvent` | Wait initiated |
| `CollabWaitingEndEvent` | Agent completed or timeout |

### Best Practices

1. **Pass all active worker IDs** - Enables event-driven processing
2. **Handle timeouts gracefully** - Worker may still be working
3. **Process completions immediately** - Don't let results queue up
4. **Call wait() in a loop** - Continue until all work is done

### Timeout Handling

If timeout occurs:
- Worker is still running (not an error)
- Call `wait()` again to continue monitoring
- Consider if task decomposition is appropriate

---

## 4. close_agent

Terminates an agent and releases resources.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Agent ID to close |

### Example

```json
{
  "id": "agent-uuid"
}
```

### Events

| Event | When |
|-------|------|
| `CollabCloseBeginEvent` | Close initiated |
| `CollabCloseEndEvent` | Agent terminated |

### When to Close

- After worker completes all assigned tasks
- When worker is no longer needed
- Before returning final response to user
- After handling errors/failures

### Important

- Always close agents to prevent resource leaks
- Track all spawned agent IDs
- Close all agents before final response

---

## Configuration Inheritance

When spawning agents, the following settings are inherited from the parent:

### Inherited Settings

- `model` (overridden by role for `worker`)
- `model_provider`
- `reasoning_effort`
- `developer_instructions`
- `base_instructions` (overridden by role)
- `user_instructions`
- `compact_prompt`
- `shell_environment_policy`
- `cwd` (working directory)
- `approval_policy`
- `sandbox_policy`

### Role Overrides

After inheritance, `AgentRole.apply_to_config()` applies role-specific settings:

| Role | Overrides |
|------|-----------|
| `default` | None |
| `orchestrator` | Base instructions → orchestrator.md |
| `worker` | Model → gpt-5.2-codex, Base instructions → gpt-5.2-codex_prompt.md |

---

## Event Summary

All collab operations emit Begin/End event pairs:

| Operation | Begin Event | End Event |
|-----------|------------|-----------|
| spawn_agent | CollabAgentSpawnBeginEvent | CollabAgentSpawnEndEvent |
| send_input | CollabAgentInteractionBeginEvent | CollabAgentInteractionEndEvent |
| wait | CollabWaitingBeginEvent | CollabWaitingEndEvent |
| close_agent | CollabCloseBeginEvent | CollabCloseEndEvent |
