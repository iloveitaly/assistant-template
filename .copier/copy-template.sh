#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

EX_REPO="${1:-/Users/mike/Projects/ai/personal-assistant}"

if [ ! -d "$EX_REPO" ]; then
    echo "Error: Source repo directory not found at $EX_REPO" >&2
    exit 1
fi

echo "Pulling ASSISTANT.md and PYTHON.md from $EX_REPO..."
cp "$EX_REPO/ASSISTANT.md" "$ROOT_DIR/ASSISTANT.md"
cp "$EX_REPO/PYTHON.md" "$ROOT_DIR/PYTHON.md"

if [ -f "$EX_REPO/scripts/cron.py" ]; then
    echo "Pulling scripts/cron.py from $EX_REPO..."
    mkdir -p "$ROOT_DIR/scripts"
    cp "$EX_REPO/scripts/cron.py" "$ROOT_DIR/scripts/cron.py"
    chmod +x "$ROOT_DIR/scripts/cron.py"
fi

echo "Done."
