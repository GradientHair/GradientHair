# Multi-Agent Usage Patterns

## Overview

This document provides concrete patterns and examples for using multi-agent workflows effectively.

---

## Pattern 1: Parallel Feature Implementation

### Scenario
Implementing multiple independent features simultaneously.

### Approach

```
Orchestrator:
1. Analyze features for independence
2. Spawn worker per feature
3. Monitor all workers with single wait()
4. Integrate results
```

### Example

```
User Request: "Add user profile page, notification system, and settings panel"

Orchestrator Actions:
1. spawn_agent(message="Implement user profile page at /profile...", agent_type="worker")
   → worker_profile_id

2. spawn_agent(message="Implement notification system...", agent_type="worker")
   → worker_notifications_id

3. spawn_agent(message="Implement settings panel at /settings...", agent_type="worker")
   → worker_settings_id

4. wait(ids=[worker_profile_id, worker_notifications_id, worker_settings_id])
   → Process each as completed

5. Verify integration between features

6. close_agent() for each worker

7. Report completion to user
```

### Key Points
- Each worker gets a distinct, well-defined scope
- Workers are informed about shared environment
- Orchestrator verifies integration after all complete

---

## Pattern 2: Code Review

### Scenario
Having an agent review code written by another agent (or yourself).

### Approach

```
1. Complete initial implementation
2. Spawn reviewer worker with fresh context
3. Provide reviewer with specific review criteria
4. Process feedback
5. Iterate if needed
```

### Example

```
After implementing a feature:

spawn_agent(
  message="Review the authentication implementation in /src/auth/.
           Check for:
           - Security vulnerabilities
           - Error handling completeness
           - Code style consistency
           - Test coverage
           Provide specific feedback with file:line references.",
  agent_type="worker"
)
→ reviewer_id

wait(ids=[reviewer_id])
→ Receive detailed review feedback

If issues found:
  spawn_agent(message="Fix issues: [specific issues from review]", agent_type="worker")
  → Continue cycle

close_agent(reviewer_id)
```

### Benefits
- Fresh context catches issues you might miss
- Separation of concerns (writing vs reviewing)
- Documented review process

---

## Pattern 3: Test-Driven Development

### Scenario
Running tests, analyzing failures, and fixing issues.

### Approach

```
1. Worker A: Run tests
2. If failures: Worker B: Fix issues
3. Repeat until all pass
```

### Example

```
# Initial test run
spawn_agent(
  message="Run the test suite with 'npm test'.
           Report all failures with error messages and stack traces.",
  agent_type="worker"
)
→ test_runner_id

wait(ids=[test_runner_id])
→ Receive test results

If failures exist:
  spawn_agent(
    message="Fix these test failures:
             - test/auth.test.ts:45 - Expected token to be valid
             - test/user.test.ts:78 - Missing required field
             Do not modify test expectations, fix the implementation.",
    agent_type="worker"
  )
  → fixer_id

  wait(ids=[fixer_id])

  # Re-run tests to verify
  send_input(id=test_runner_id, message="Run tests again to verify fixes")
  wait(ids=[test_runner_id])

close_agent() for all
```

### Benefits
- Test output stays in worker context, not polluting orchestrator
- Clear separation: test runner vs fixer
- Iterative until success

---

## Pattern 4: Research and Implementation

### Scenario
Researching a topic and then implementing based on findings.

### Approach

```
1. Worker A: Research/exploration
2. Orchestrator: Synthesize findings
3. Worker B: Implementation based on research
```

### Example

```
# Research phase
spawn_agent(
  message="Explore the codebase to understand:
           - Current database connection handling
           - Existing caching mechanisms
           - Configuration patterns used
           Report findings with specific file references.",
  agent_type="worker"
)
→ researcher_id

wait(ids=[researcher_id])
→ Receive research findings

# Implementation phase (informed by research)
spawn_agent(
  message="Based on the codebase patterns:
           - DB connections use pool in /src/db/pool.ts
           - Caching uses Redis client in /src/cache/
           - Config loaded from /src/config/

           Implement connection caching following these patterns.
           Match existing code style.",
  agent_type="worker"
)
→ implementer_id

wait(ids=[implementer_id])
close_agent() for all
```

### Benefits
- Research context doesn't bloat implementation context
- Implementation is informed by actual codebase patterns
- Clean separation of exploration vs execution

---

## Pattern 5: Log-Heavy Operations

### Scenario
Operations that produce large amounts of output (builds, migrations, etc).

### Approach

```
Delegate to worker to:
1. Contain verbose output
2. Summarize results
3. Preserve orchestrator context
```

### Example

```
spawn_agent(
  message="Run the full build process:
           1. npm install
           2. npm run build
           3. npm run lint

           If any step fails, report the specific error.
           If all succeed, report 'Build successful' with any warnings.",
  agent_type="worker"
)
→ builder_id

wait(ids=[builder_id], timeout_ms=300000)  # 5 min for builds
→ Receive summary, not full logs

close_agent(builder_id)
```

### Benefits
- Build logs stay in worker context
- Orchestrator gets concise summary
- Context preserved for follow-up tasks

---

## Pattern 6: Divide and Conquer Refactoring

### Scenario
Large refactoring across many files.

### Approach

```
1. Analyze scope and dependencies
2. Identify independent refactoring units
3. Assign workers to each unit
4. Coordinate shared changes
5. Verify consistency
```

### Example

```
User Request: "Rename 'userId' to 'accountId' across the codebase"

Orchestrator Analysis:
- /src/models/ - 15 files
- /src/api/ - 20 files
- /src/services/ - 12 files
- /tests/ - 25 files

Spawn workers for independent directories:

spawn_agent(message="Rename userId→accountId in /src/models/...", agent_type="worker")
spawn_agent(message="Rename userId→accountId in /src/api/...", agent_type="worker")
spawn_agent(message="Rename userId→accountId in /src/services/...", agent_type="worker")
spawn_agent(message="Rename userId→accountId in /tests/...", agent_type="worker")

wait() for all, process completions

Verify consistency:
spawn_agent(
  message="Verify no remaining 'userId' references. Run type check to confirm.",
  agent_type="worker"
)

close_agent() for all
```

### Benefits
- Parallelized execution
- Each worker has focused scope
- Final verification catches inconsistencies

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Micromanaging Workers

```
❌ Bad:
spawn_agent("Start implementing auth")
wait()
send_input("Now add login function")
wait()
send_input("Now add logout function")
wait()
send_input("Now add session management")
wait()

✅ Good:
spawn_agent("Implement complete auth module: login, logout, session management")
wait()
```

### Anti-Pattern 2: Status Check Messages

```
❌ Bad:
spawn_agent("Implement feature X")
# 10 seconds later
send_input("How's it going?")
send_input("Are you done yet?")

✅ Good:
spawn_agent("Implement feature X")
wait()  # Just wait
```

### Anti-Pattern 3: Overlapping Worker Scopes

```
❌ Bad:
spawn_agent("Update /src/auth/login.ts")
spawn_agent("Update /src/auth/login.ts")  # Same file!

✅ Good:
spawn_agent("Update /src/auth/login.ts - add validation")
spawn_agent("Update /src/auth/logout.ts - add logging")
```

### Anti-Pattern 4: Forgetting to Close

```
❌ Bad:
spawn_agent("Task 1") → id1
spawn_agent("Task 2") → id2
wait()
# Return to user without closing

✅ Good:
spawn_agent("Task 1") → id1
spawn_agent("Task 2") → id2
wait()
close_agent(id1)
close_agent(id2)
# Then return to user
```

---

## Decision Guide: When to Use Multi-Agent

### Use Multi-Agent When:

| Scenario | Reason |
|----------|--------|
| Multiple independent subtasks | Parallelization benefits |
| Need fresh perspective | Code review, idea validation |
| Log-heavy operations | Context preservation |
| Large scope refactoring | Divide and conquer |
| Long-running operations | Worker isolation |

### Don't Use Multi-Agent When:

| Scenario | Reason |
|----------|--------|
| Simple, single-file change | Overhead not justified |
| Highly interdependent tasks | Sequential anyway |
| Quick fixes | Faster to do directly |
| Exploratory work | Need interactive feedback |

### Rule of Thumb

```
If task can be completed in < 3 focused steps → Do directly
If task has 3+ independent parts OR needs isolation → Consider multi-agent
```
