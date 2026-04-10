#!/usr/bin/env bash
# ruff-check-file.sh — Run ruff check on a single file.
# Used as a Claude Code PostToolUse hook for instant feedback.
# Reads JSON from stdin with tool_input.file_path.
# Exit code 2 = blocking error (feedback to Claude via stderr).

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[[ -z "$FILE_PATH" ]] && exit 0
[[ "$FILE_PATH" == *.py ]] || exit 0

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Resolve to absolute path if relative
[[ "$FILE_PATH" == /* ]] || FILE_PATH="$ROOT_DIR/$FILE_PATH"

# Determine which package this file belongs to
REL_PATH="${FILE_PATH#"$ROOT_DIR"/}"
PKG_DIR="${REL_PATH%%/*}"

case "$PKG_DIR" in
    mcr-core|mcr-gateway|mcr-generation|mcr-capture-worker)
        OUTPUT=$(cd "$ROOT_DIR/$PKG_DIR" && uv run ruff check "$FILE_PATH" 2>&1)
        if [[ $? -ne 0 ]]; then
            echo "$OUTPUT" >&2
            exit 2
        fi
        ;;
esac
