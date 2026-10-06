set shell := ["zsh", "-c"]
set script-interpreter := ["zsh", "-e"]

# upstream repository configuration
upstream_repo := "https://github.com/iloveitaly/llm-ide-rules/blob/master"

alias generate-python-instructions := generate_python_instructions

# pull upstream rules and generate PYTHON.md
generate_python_instructions:
    just _retrieve {{upstream_repo / ".github/copilot-instructions.md"}}
    just _retrieve {{upstream_repo / ".github/instructions/python.instructions.md"}}
    just _retrieve {{upstream_repo / ".opencode/commands/standalone-python-scripts.md"}}
    cat .github/copilot-instructions.md > PYTHON.md
    echo "" >> PYTHON.md
    sed '/^---$/,/^---$/d' .github/instructions/python.instructions.md >> PYTHON.md
    echo "" >> PYTHON.md
    cat .opencode/commands/standalone-python-scripts.md >> PYTHON.md
    printf "\n<!-- END CLONED INSTRUCTIONS -->\n" >> PYTHON.md

# run scheduled jobs via tasker
cron *args:
    tasker -file Cronfile {{args}}

[private]
[script]
_retrieve url:
    # extract the path after blob/<branch>/
    file_path=$(echo "{{url}}" | sed -E 's/.*blob\/[^\/]+\/(.*)/\1/')
    
    print "Downloading {{url}} -> $file_path"
    mkdir -p "$(dirname "$file_path")"
    http --follow --download "{{url}}?raw=true" --output "$file_path"

