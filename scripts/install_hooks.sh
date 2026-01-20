#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$ROOT_DIR/.git/hooks"
TEMPLATE_DIR="$ROOT_DIR/scripts/hooks"

mkdir -p "$HOOKS_DIR"
cp "$TEMPLATE_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
cp "$TEMPLATE_DIR/post-commit" "$HOOKS_DIR/post-commit"
chmod +x "$HOOKS_DIR/pre-commit" "$HOOKS_DIR/post-commit"

echo "[hooks] Installed pre-commit and post-commit hooks."
