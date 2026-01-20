#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
STAMP_FILE="$ROOT_DIR/.last_test_run"

# No explicit smoke tests configured; just update the timestamp.
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$STAMP_FILE"
echo "[run_smoke] Updated $STAMP_FILE"
