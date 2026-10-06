# Assistant Workspace Template

A template for creating agentic AI assistant workspaces, designed for use with OpenCode, Claude Code, Cursor, Codex, Antigravity, and other LLM developer environments.

GitHub Repository: [https://github.com/iloveitaly/assistant-template](https://github.com/iloveitaly/assistant-template)

## Usage

Create a new directory for your assistant workspace:

```shell
mkdir my-assistant
cd my-assistant
```

Instantiate the template using Copier:

```shell
uv tool run --with jinja2_shell_extension copier@latest copy --trust --vcs-ref=HEAD https://github.com/iloveitaly/assistant-template .
```

Or using the GitHub shorthand:

```shell
uv tool run --with jinja2_shell_extension copier@latest copy --trust --vcs-ref=HEAD gh:iloveitaly/assistant-template .
```

## What is Provided?

Here are the key tools and features provided:

1. **`AGENTS.md`**: Top-level entrypoint for AI coding agents linking directly to [`ASSISTANT.md`](./ASSISTANT.md) and [`PYTHON.md`](./PYTHON.md).
2. **`ASSISTANT.md`**: Architectural framework and behavioral conventions for autonomous agents:
   - Behavioral governance and system constraints in `rules/`
   - Persistent facts and process state in `memories/`
   - Procedures and workflows in `sops/`
   - External data provenance and caches in `data/`
   - Executable helpers in `scripts/`
3. **`PYTHON.md`**: Standalone Python scripting instructions optimized for LLM/agent code generation (PEP 723 `uv` inline metadata, `cyclopts` CLI parsing, and `pydantic` validation).
4. **`Justfile`**: Task runner interface:
   - `just setup-mcp`: Adds and registers MCP servers across client configurations (`opencode`, `claude code`, `antigravity`, `codex`, `cursor`) via `mcp-add`.
   - `just cron`: Runs the foreground cron scheduler.
   - `just initial_wake`: Executes due jobs once on system wake.
5. **`cron.yml` & `scripts/cron.py`**: AnyIO-based concurrent cron scheduler featuring:
   - Calendar recurrence intervals (`hourly`, `daily`, `weekly`, `monthly`, `yearly`) anchored to local midnight.
   - Concurrency locking via `flock` in `tmp/cron/`.
   - SQLite execution history and result storage in `data/cron/jobs.sqlite3`.
   - Execution modes for shell commands and markdown prompt jobs (`agy`).
6. **`mise.toml`**: Automatic tool version management configuring `python = "latest"` and `uv = "latest"`.
7. **Template Automation (`.copier/`)**:
   - `.copier/generate-python-instructions.sh`: Downloads upstream LLM rules into an isolated temporary folder and generates `PYTHON.md`.
   - `.copier/copy-template.sh`: Pulls updated core files (`ASSISTANT.md`, `PYTHON.md`, `scripts/cron.py`) from reference repositories.

## Updating

To sync an existing assistant workspace with future template changes:

```shell
uv tool run --with jinja2_shell_extension copier@latest update --trust
```
