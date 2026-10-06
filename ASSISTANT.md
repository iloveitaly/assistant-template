# Assistant folder instructions

## Find the relevant instructions before acting

1. Read the rules for each system or concern you will work with. An index description tells you what a file covers; read the linked file for the actual constraints.
2. Follow only the SOPs explicitly provided by the user. Do not search for, select, or open additional SOPs, including those referenced by another file. When no SOP is provided, work from the user's request and the relevant rules and context.
3. Use `memories/AGENTS.md` to locate relevant context and process state. Read the relevant entries and check dates and sources before relying on information that may have changed.
4. Before using stored data, consult `data/AGENTS.md` for the available files, their formats, source authority, and provenance. Before editing files, read any applicable directory instructions.

## System checks

- Confirm that the MCPs required for the task are connected and usable before beginning work that depends on them.
- If a required MCP is missing, disconnected, timing out, or failing, stop the dependent work early. Immediately tell the user which system failed and what you were trying to do.
- Retry the intended tool once if the failure looks transient. If it still fails, report and wait.
- Do not search for or attempt workarounds through alternate APIs, local scripts, browsers, or substitute data sources unless the user explicitly asks for one.

## Know where information belongs

Use the paths identified by the root `AGENTS.md`. Paths below are relative to the current project folder:

```text
AGENTS.md            # shared instructions and links to folder indexes
rules/               # behavioral and system constraints
  AGENTS.md          # instructions for maintaining rule files
memories/            # factual context and process state
  AGENTS.md          # index of available memories and state files
sops/                # procedures explicitly invoked by the user
data/                # non-Markdown files derived from external systems
  AGENTS.md          # index of system data files and reading guidance
  amazon/
    order_history.jsonl
scripts/             # system subfolders and general-purpose helpers
  AGENTS.md          # index of available scripts
  amazon/
    export_amazon_order_history.py
  validate_assistant_folder_links.py
Justfile             # setup, cleanup, wake, and scheduled commands
cron.yml             # job names, recurrence, commands or prompts, and optional timeouts
tmp/                 # local runtime files, including per-job locks
```

Procedure directories may reflect the work, such as `personal-sops/`. Store system data under `data/`, with one subfolder per source system. Create a directory only when it has a file to hold; a system does not need every component shown above.

## Maintain links in `AGENTS.md`

Keep the root `AGENTS.md` concise. Put shared instructions there and link to detailed rules and the indexes in `memories/AGENTS.md`, `data/AGENTS.md`, and `scripts/AGENTS.md`. Maintain each folder's inventory in its own index. SOPs are supplied with the task and do not need an index for automatic discovery.

Describe each linked file's scope. For example, use “Todoist: task creation permissions and due-date defaults” as the index description, and maintain the actual permissions and defaults in the rule file.

Keep an `AGENTS.md` index in each of `memories/`, `data/`, and `scripts/`. List the files and system subfolders that exist, with relative links and short descriptions of their purpose. Include both system-specific and top-level scripts in the scripts index. Update the appropriate index when adding, moving, or removing a file, and repair affected links. Keep detailed information in one authoritative place.

## Use rules to govern your behavior

Apply the relevant rules during both documented procedures and ad-hoc requests. Rules cover constraints such as ownership, permissions, formatting, update semantics, and required tool parameters.

When maintaining rules, use one file per system or concern and follow `rules/AGENTS.md`. Write short, enforceable instructions. Keep ordered workflow steps in an SOP and factual context in memories.

Classify information by its purpose. A birthday is a fact even though it stays the same. A recorded preference is factual context; an instruction governing how you act on that preference is a rule. When a rule depends on a stored fact, link to its authoritative location.

Link from SOPs to the rules they follow. Keep rules applicable on their own, without dependencies on or indexes of particular SOPs.

## Use memories for facts and process state

Use `memories/AGENTS.md` to find factual context and the current state of ongoing work. The indexed files can contain stable facts, recorded preferences, relationships, changing circumstances, and cursors. Keep the facts and state values in those files; use the index to describe what each file holds.

When maintaining a memory, attach sources and dates to information that may change or need verification. State when a fact was observed or confirmed. Recheck information when its age or a known change matters to the task. Label uncertainty and conflicting information, and retain enough source detail to resolve it. Keep standing behavioral instructions in rules.

Treat a cursor as a record of completed work. When following a provided SOP, use its definition of fields such as `last_checked_at` and verify the required results before advancing them. Store current values in the memory and update instructions in the SOP. A reference to an owning SOP identifies the process; it does not authorize loading that SOP. Add persistent state only when the process needs it.

## Follow and maintain SOPs

An SOP, or standard operating procedure, is a workflow explicitly invoked and provided by the user. Read the provided SOP's scope, inputs, completion criteria, and partial-failure handling before executing its steps. Apply its linked rules throughout the work. A reference to another SOP does not invoke it; follow that SOP only if the user also explicitly provides it.

When asked to create or edit an SOP, use ordinary Markdown sections:

| Section | What to record |
|---|---|
| Objective | The result the process produces |
| Rules | Links to the constraints that govern the work |
| Scope | The work covered by the SOP once the user invokes it |
| Inputs | Required information, sources, scope, and any saved state |
| Actions and outputs | What changes, what is produced, and where the result goes |
| Completion | Observable results that establish success and how to verify them |
| Heartbeat (optional) | A URL to GET after successful completion and any required state updates |
| Partial failure | What stops, what can continue independently, and how to account for completed actions |
| Procedure | Ordered steps, grouped into phases when useful |

Define completion through results you can verify. For example, a message-review SOP can require complete retrieval of the requested interval and delivery of the review before advancing its cursor. Specify which failures leave the cursor unchanged and how to revisit unfinished work. For workflows that change an external system, explain how a retry avoids repeating actions already completed.

Include only applicable sections and fields. Keep operating instructions in the Markdown body. Add frontmatter only when a concrete tool consumes metadata such as a description or system name.

### Heartbeat

An SOP can include an optional `Heartbeat` section containing a single URL:

```markdown
## Heartbeat

https://example.com/heartbeat
```

After verifying all completion criteria and required state updates, send an HTTP GET to that URL and check for a successful response. Omit the request when the section is absent or the workflow is incomplete. If the request fails, report the heartbeat delivery failure separately without rerunning the completed workflow.

### Commit memory changes

After the SOP completes and its heartbeat request finishes, commit any added, modified, or deleted files under `memories/`. If no heartbeat is configured, commit after verifying completion and state updates. A heartbeat delivery failure does not prevent committing memory updates from the completed workflow.

Use the commit message `Update memories`. Include only changes under `memories/`, excluding any unrelated staged files. Skip the commit when there are no changes in that directory.

## Store system data in `data/`

Store non-Markdown files derived from external systems in `data/`. Use a subfolder named for each source system, such as `data/amazon/order_history.jsonl`. JSON, JSONL, PDFs, and other exported or extracted files belong in the corresponding system's subfolder. The folder's `AGENTS.md` holds its index and reading guidance.

Index system subfolders and data files in `data/AGENTS.md`. Describe file formats, naming conventions, authoritative sources, and provenance alongside the relevant entries so data can be read without loading an SOP. Put ordered update steps in the owning SOP; references to that SOP identify it without invoking it. Link to the state file when applicable.

Retain source references such as record IDs, URLs, or original filenames so values can be traced back to their source system. Preserve saved original files. When extracting records from them, identify the source file and a useful location within it, such as a page or record ID.

Use structured records for routine queries. Check the original when a value is disputed, ambiguous, or needs source verification. Treat the original as authoritative for what that source says. Correct extraction errors in derived records while preserving the original and its reference. When original sources disagree, record the conflict and follow the collection's authority rules.

## Use scripts for deterministic work

Use `scripts/AGENTS.md` to locate helpers for operations such as paging, cursor conversion, and parsing. Follow the inputs, outputs, and failure behavior documented in the script or the provided SOP.

Organize system-specific scripts in a subfolder named for that system, using the same names as `data/`. For example, Amazon helpers belong in `scripts/amazon/`. Place scripts that are not tied to a particular system directly under `scripts/`.

Use descriptive filenames that identify the system and specific operation, even within a system subfolder: for example, `export_amazon_order_history.py`. For workspace-wide scripts, name the scope and operation, such as `validate_assistant_folder_links.py`. Avoid generic names such as `cleanup.py`, `utils.py`, or `helpers.py`.

Add a helper when a workflow repeatedly reconstructs the same mechanical operation. Add its path and purpose to `scripts/AGENTS.md`, and document invocation details in the script. Link to it from the SOP being maintained when applicable. Keep MCP server implementations in their own repositories; record how to launch or connect to them in this folder.

## Use the Justfile for repository commands

Keep these commands in the top-level `Justfile`:

| Command | Purpose |
|---|---|
| `just setup` | Configure MCPs and other state required by the repository |
| `just cleanup` | Remove lingering state from the repository |
| `just initial_wake` | Run commands needed on wake, including due jobs |
| `just cron` | Run the foreground scheduler for `cron.yml` |

Run these commands from the project root. Keep MCP registrations and client selection in `setup`, and apply registrations through `mcp-add`. Leave generated client configuration files alone. Document required environment variables and supporting processes alongside the relevant command.

## Maintain scheduled jobs in cron.yml

Define jobs in the top-level `cron.yml`, keyed by a descriptive, stable job name. Each job has a `recurrence` and exactly one of `command` or `prompt`; an optional `timeout_seconds` overrides the one-hour default. Keep reusable job logic in the appropriate `scripts/` location. Launch the runner from the assistant folder. Its top-level path constants use that working directory for `cron.yml`, `data/cron/jobs.sqlite3`, and `tmp/cron/`. Commands run there in a non-interactive zsh login shell and must stay in the foreground until their work finishes. `--config` changes only the YAML file to read.

`command` supplies a shell command. `prompt` references an existing markdown file, relative to the working directory or by absolute path. Prompt jobs use Antigravity (`agy`) as the default harness, running `agy --dangerously-skip-permissions --print '@/absolute/path/to/prompt.md'`. The runner passes the file reference without reading or expanding its contents. Prompt jobs share command jobs' locks, timeouts, output capture, and exit-status handling; history records the generated harness command.

Supported recurrences are `hourly`, `daily`, `weekly`, `monthly`, and `yearly`. Each job is due until it succeeds in the current calendar period in America/Denver; weeks start on Monday. Missed periods coalesce into one run at the next check. Failures and timeouts remain due for the next check. Keep job commands safe to retry after partial completion.

`daily` means one successful run per local calendar date, becoming due again at midnight in the configured timezone. It does not wait 24 hours after the previous run; daylight saving changes can make a calendar day 23 or 25 hours long.

For `hourly`, `daily`, and `weekly`, add a positive integer `every` to group that many calendar periods; it defaults to 1. For example, `recurrence: daily` with `every: 2` runs every other local calendar day. The first attempt is due immediately and anchors the schedule to its current hour, date, or Monday-start week, without a start-date setting. Hours count real hours across DST; days and weeks follow the local calendar. The earliest attempt, including a failed attempt, preserves the anchor in SQLite across retries and restarts. Missed intervals coalesce into one run. Changing `recurrence` or `every` selects a separate schedule history; returning to a previous definition resumes that schedule's anchor. Monthly and yearly jobs use `every: 1`.

Use `just cron` to run the foreground scheduler, which checks immediately and every 60 seconds using an AnyIO polling loop. Each job has at most one active task, so long-running jobs do not delay checks of other jobs. Use `just initial_wake` for a single catch-up check that waits for due jobs; the wake mechanism must call it. These commands do not install a background service or register a wake hook. Restart the scheduler after changing `cron.yml`.

The runner executes different jobs in parallel and prevents overlapping runs of the same job with `flock` files in `tmp/cron/`. Do not delete these files while jobs are running. Keep SQLite run history in `data/cron/jobs.sqlite3`, outside `tmp/`; deleting it makes every job due again. Each attempt records its start, completion, command, status, exit code, stdout, and stderr. The runner also streams output to the terminal. Single-check mode returns a nonzero exit status if any executed job fails or times out; the daemon keeps checking after command failures. A workspace-wide scheduler lock prevents duplicate daemons, while wake checks can safely coexist with the daemon. SIGINT/SIGTERM stop active process groups and persist their interrupted results before releasing locks.

A forced runner kill can leave an unfinished history entry without final logs. The foreground command inherits its lock; once that lock is released, a later invocation marks the abandoned attempt interrupted and retries when due. The runner does not discover or invoke SOPs independently of the configured commands.

## Check your changes

After maintaining these files, verify relative links and update affected indexes. Check that rules, facts, and state values each have one authoritative home, that SOPs link to their dependencies, and that source references still resolve.
