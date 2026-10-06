#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

UPSTREAM_REPO="https://github.com/iloveitaly/llm-ide-rules/blob/master"

retrieve() {
    local url="$1"
    # extract the path after blob/<branch>/
    local file_path
    file_path=$(echo "$url" | sed -E 's/.*blob\/[^\/]+\/(.*)/\1/')

    echo "Downloading $url -> $file_path"
    mkdir -p "$(dirname "$file_path")"
    if command -v http >/dev/null 2>&1; then
        http --follow --download "${url}?raw=true" --output "$file_path"
    else
        curl -fSL "${url}?raw=true" -o "$file_path"
    fi
}

retrieve "$UPSTREAM_REPO/.github/copilot-instructions.md"
retrieve "$UPSTREAM_REPO/.github/instructions/python.instructions.md"
retrieve "$UPSTREAM_REPO/.opencode/commands/standalone-python-scripts.md"

cat .github/copilot-instructions.md > PYTHON.md
echo "" >> PYTHON.md
sed '/^---$/,/^---$/d' .github/instructions/python.instructions.md >> PYTHON.md
echo "" >> PYTHON.md
cat .opencode/commands/standalone-python-scripts.md >> PYTHON.md
printf "\n<!-- END CLONED INSTRUCTIONS -->\n" >> PYTHON.md
