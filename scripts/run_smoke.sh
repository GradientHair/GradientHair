#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP_FILE="$ROOT_DIR/.last_test_run"

python3 -m py_compile \
  "$ROOT_DIR/backend/agents/principle_agent.py" \
  "$ROOT_DIR/backend/agents/topic_agent.py" \
  "$ROOT_DIR/backend/agents/safety_orchestrator.py" \
  "$ROOT_DIR/backend/agents/review_agent.py" \
  "$ROOT_DIR/backend/server.py"

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$STAMP_FILE"
echo "[smoke] tests ok. stamp written to $STAMP_FILE"
