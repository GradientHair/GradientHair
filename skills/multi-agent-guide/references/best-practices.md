# Multi-Agent Best Practices

## 1. Orchestrator Principles

### Core Tenets

1. **Never stop monitoring**
   - While any worker is active, continuously watch via `wait()`
   - Don't assume completion without verification

2. **Be patient**
   - Allow workers time to complete their tasks
   - Don't send unnecessary status check messages
   - Trust the worker to do its job

3. **Never return until fully complete**
   - Verify all work before responding to user
   - Ensure integration between worker outputs
   - Validate final results meet requirements

### Orchestrator Workflow

```
Step 1: Task Analysis
├── Understand the full scope of the request
├── Identify parallelizable subtasks
└── Determine optimal worker configuration

Step 2: Worker Spawning
├── Create workers with clear, specific goals
├── Include constraints and boundaries
├── Define expected outputs/deliverables
└── Inform workers about shared environment

Step 3: Monitoring Loop
├── Call wait() with all active worker IDs
├── Process completed workers immediately
├── Verify output accuracy and completeness
└── Check for conflicts with other workers

Step 4: Issue Resolution
├── If problems found, assign fixes to workers
├── Don't attempt fixes yourself (delegate!)
└── Return to monitoring after new assignments

Step 5: Cleanup
├── close_agent() for completed workers
├── Ensure no orphaned agents remain
└── Return to user only when everything is done
```

## 2. Worker Execution Semantics

### Key Understanding

- **No intermediate state observation** - You cannot see what a worker is doing mid-execution
- **Fully autonomous** - Workers can execute commands, modify/create/delete files
- **Message queuing** - `send_input` messages are processed only after worker completes (unless interrupt=true)

### Implications

| Do | Don't |
|------|--------|
| Monitor with `wait()` only | Send status check messages |
| Give complete initial instructions | Drip-feed information |
| Use `send_input` for next task | Use `send_input` to "check in" |
| Let workers work independently | Micromanage worker progress |

## 3. Interrupt Usage Guide

### When to Use `interrupt=true`

- Current task needs to be changed/stopped/redirected
- Critical new information invalidates ongoing work
- User explicitly requests cancellation

### When NOT to Use Interrupt

- Worker is taking longer than expected (be patient)
- You want a status update (use `wait()` instead)
- You have additional information that can wait

### Best Practice

```
Use interrupt sparingly and intentionally.
If in doubt, wait for natural completion.
```

## 4. Collaboration Rules

### Shared Environment

Workers operate in the same filesystem and environment:

```
Worker A creates: /project/feature-a/component.ts
Worker B creates: /project/feature-b/service.ts
Both see each other's files after creation
```

**Always inform workers:**
- They share the environment with other workers
- Other workers may be modifying files concurrently
- They should not overwrite or undo other workers' changes

### Conflict Prevention

1. **Assign distinct scopes** - Each worker should have clearly separated responsibilities
2. **Avoid file overlap** - Don't assign multiple workers to the same files
3. **Communicate boundaries** - Tell workers which areas belong to other workers
4. **Verify integration** - After completion, check that outputs work together

### No Infinite Recursion

By default, workers cannot spawn sub-agents. This prevents:
- Runaway resource consumption
- Unpredictable execution chains
- Loss of orchestrator control

If sub-agent spawning is needed, it must be explicitly enabled.

## 5. Parallel Monitoring

### Multi-Worker Wait Pattern

```json
{
  "ids": ["worker-a-id", "worker-b-id", "worker-c-id"],
  "timeout_ms": 60000
}
```

Benefits:
- Event-driven workflow
- Returns immediately when ANY worker completes
- Efficient resource utilization
- Natural handling of varying completion times

### Processing Completed Workers

```
1. wait() returns with completed worker info
2. Process that worker's output
3. Optionally assign follow-up task
4. Remove from active list if done, or keep for next task
5. Return to wait() with updated worker list
```

## 6. Error Handling

### Worker Failure

If a worker reports failure or produces incorrect output:
1. Analyze the error/issue
2. Decide: retry same worker or spawn new one
3. Provide corrective instructions
4. Continue monitoring

### Timeout Handling

If `wait()` times out:
1. Worker is still running (task may be complex)
2. Call `wait()` again with same IDs
3. If consistently timing out, evaluate if task is too large
4. Consider breaking down further or using `interrupt` if stuck

## 7. Resource Management

### Cleanup

Always call `close_agent()` when:
- Worker has completed all assigned tasks
- Worker is no longer needed
- Before returning to user

### Avoid Orphaned Agents

```
Good: Track all spawned worker IDs
Good: close_agent() for each before final response
Bad:  Return to user with workers still active
Bad:  Forget to close workers after errors
```
