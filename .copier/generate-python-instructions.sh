#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

UPSTREAM_REPO="https://github.com/iloveitaly/llm-ide-rules/blob/master"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/python-instructions.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

retrieve() {
    local url="$1"
    # extract the path after blob/<branch>/
    local relative_path
    relative_path=$(echo "$url" | sed -E 's/.*blob\/[^\/]+\/(.*)/\1/')
    local dest_path="$TMP_DIR/$relative_path"

    echo "Downloading $url -> $dest_path"
    mkdir -p "$(dirname "$dest_path")"
    if command -v http >/dev/null 2>&1; then
        http --follow --download "${url}?raw=true" --output "$dest_path"
    else
        curl -fSL "${url}?raw=true" -o "$dest_path"
    fi
}

retrieve "$UPSTREAM_REPO/.github/copilot-instructions.md"
retrieve "$UPSTREAM_REPO/.github/instructions/python.instructions.md"
retrieve "$UPSTREAM_REPO/.opencode/commands/standalone-python-scripts.md"

cat "$TMP_DIR/.github/copilot-instructions.md" > PYTHON.md
echo "" >> PYTHON.md
sed '/^---$/,/^---$/d' "$TMP_DIR/.github/instructions/python.instructions.md" >> PYTHON.md
echo "" >> PYTHON.md
cat "$TMP_DIR/.opencode/commands/standalone-python-scripts.md" >> PYTHON.md
printf "\n<!-- END CLONED INSTRUCTIONS -->\n" >> PYTHON.md
