#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "activemodel==0.25.0",
#   "anyio>=4,<5",
#   "cyclopts>=5.1,<6",
#   "pydantic>=2,<3",
#   "pyyaml>=6,<7",
#   "rich>=14,<15",
#   "structlog-config>=0.15.0",
#   "whenever>=0.11,<0.12",
# ]
# ///

"""Run due cron.yml jobs concurrently and retain their results in SQLite.

Usage: ./scripts/cron.py [--help]

By default, check immediately and then poll until stopped. With --once (used on
wake), check every configured job once, run due jobs in parallel, wait for them
to finish, and exit without polling or retrying. Skip jobs that already succeeded
in their current calendar period or whose lock is held by another worker. Exit
with status 1 if an executed job fails or times out, otherwise 0.

Only successful runs satisfy a calendar period; missed periods coalesce into one
run for the current period. Commands must stay in the foreground so their exit
status represents completed work.
"""

import codecs
import errno
import fcntl
import os
import re
import signal
import shlex
import subprocess
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from shutil import which
from typing import Annotated, Literal, Self, TextIO

import activemodel
import anyio
from cyclopts import App, Parameter
import structlog
import yaml
from pydantic import (
    BaseModel, ConfigDict, Field, FilePath, PositiveInt, StringConstraints,
    TypeAdapter, ValidationError, model_validator,
)
from rich.console import Console
from anyio.abc import ByteReceiveStream, Process, TaskGroup, TaskStatus
from sqlmodel import Field as SQLField, SQLModel
from structlog_config import configure_logger
from whenever import Instant, ZonedDateTime


WORKING_DIRECTORY = Path.cwd()

CONFIG_PATH = WORKING_DIRECTORY / "cron.yml"

DATABASE_PATH = WORKING_DIRECTORY / "data" / "cron" / "jobs.sqlite3"

LOCK_DIRECTORY = WORKING_DIRECTORY / "tmp" / "cron"

SCHEMA_LOCK_PATH = LOCK_DIRECTORY / "schema.lock"
"Serialize WAL setup and first-time schema creation across runners"

SCHEDULER_LOCK_PATH = LOCK_DIRECTORY / "scheduler.lock"
"Allow one scheduler per workspace; commands do not inherit this lock"

JOB_LOCK_FILENAME = "job-{name}.lock"
"Prevent overlapping runs of a job; commands inherit this lock descriptor"

SHELL_PATH = which("zsh")
assert SHELL_PATH is not None, "zsh must be available on PATH"

DEFAULT_TIMEOUT_SECONDS = 3_600

DEFAULT_TIMEZONE = "America/Denver"

DEFAULT_CHECK_INTERVAL_SECONDS = 60

DEFAULT_HARNESS = "agy"
"Antigravity CLI used to execute markdown prompts in dangerous mode"

# keep runner diagnostics separate from the job's stdout
log = configure_logger(logger_factory=structlog.PrintLoggerFactory(file=sys.stderr))

# job names become lock filenames, so exclude path separators and traversal
JOB_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", re.VERBOSE)

type Recurrence = Literal["hourly", "daily", "weekly", "monthly", "yearly"]

type JobName = Annotated[str, StringConstraints(pattern=JOB_NAME_PATTERN)]

type NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class RunnerOptions(BaseModel):
    "Validate command-line options before initializing history or dispatching jobs"

    model_config = ConfigDict(extra="forbid", validate_default=True)

    config: FilePath = Field(default=CONFIG_PATH, description="Path to the job definitions")
    timezone: str = Field(default=DEFAULT_TIMEZONE, description="Timezone for calendar periods")
    timeout_seconds: PositiveInt = Field(
        default=DEFAULT_TIMEOUT_SECONDS, description="Default job timeout in seconds",
    )
    check_interval_seconds: float = Field(
        default=DEFAULT_CHECK_INTERVAL_SECONDS, gt=0, allow_inf_nan=False,
        description="Seconds between scheduler checks",
    )
    once: bool = Field(
        default=False,
        description="Check all jobs once, wait for due jobs to finish, and exit without polling",
    )


class JobConfig(BaseModel):
    "Validate a job's calendar interval, execution source, and optional timeout"

    model_config = ConfigDict(extra="forbid", strict=True)

    recurrence: Recurrence
    every: PositiveInt = 1
    command: NonEmptyString | None = None
    prompt: NonEmptyString | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def require_one_execution_source(self) -> Self:
        if (self.command is None) == (self.prompt is None):
            raise ValueError("specify exactly one of command or prompt")

        return self

    @model_validator(mode="after")
    def validate_every(self) -> Self:
        if self.every != 1 and self.recurrence not in {"hourly", "daily", "weekly"}:
            raise ValueError("every is supported only for hourly, daily, and weekly recurrences")

        return self

    @property
    def schedule_key(self) -> str:
        # include the interval in history without changing the existing SQLite schema
        return self.recurrence if self.every == 1 else f"{self.recurrence}:{self.every}"


class JobRun(activemodel.BaseModel, table=True):
    "Persist one execution attempt and its result for history and due checks"

    id: int | None = SQLField(default=None, primary_key=True)
    job_name: str = SQLField(index=True)
    recurrence: str
    period: str
    command: str
    timeout_seconds: float
    status: str = "running"
    # utc iso strings preserve timezone information in SQLite
    started_at: str
    finished_at: str | None = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None


def load_jobs(config_path: Path) -> dict[str, JobConfig]:
    "Validate every job and prompt reference before dispatch or history creation"

    raw_config = yaml.safe_load(config_path.read_text())
    jobs = TypeAdapter(dict[JobName, JobConfig]).validate_python(raw_config)
    # validate prompt references before initializing history or dispatching any jobs
    for job in jobs.values():
        build_job_command(job)

    return jobs


def build_job_command(job: JobConfig) -> str:
    "Return a shell command or construct a safely quoted markdown harness invocation"

    if job.command is not None:
        return job.command

    assert job.prompt is not None
    prompt_path = (WORKING_DIRECTORY / job.prompt).resolve(strict=True)
    if not prompt_path.is_file() or prompt_path.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError(f"prompt must reference a markdown file: {prompt_path}")

    # pass the reference as one shell argument, including paths with spaces or metacharacters
    return shlex.join([
        DEFAULT_HARNESS, "--dangerously-skip-permissions", "--print", f"@{prompt_path}"
    ])


def period_key(recurrence: Recurrence, now: ZonedDateTime) -> str:
    "Identify the current local calendar period, distinguishing repeated DST hours"

    date = now.date()

    match recurrence:
        case "hourly":
            # include the UTC offset so the repeated DST hour has its own period
            return now.to_fixed_offset().format_iso(unit="second")[:13] + str(now.offset)
        case "daily":
            return date.format_iso()
        case "weekly":
            return date.subtract(days=date.day_of_week().value - 1).format_iso()
        case "monthly":
            return f"{now.year:04}-{now.month:02}"
        case "yearly":
            return f"{now.year:04}"


def calendar_units_since(recurrence: Recurrence, now: ZonedDateTime, anchor: ZonedDateTime) -> int:
    "Count calendar days or Monday-start weeks, and real hours across DST changes"

    if recurrence == "hourly":
        # align real-time hours to local boundaries without merging the repeated DST hour
        current_hour = now.timestamp() - now.minute * 60 - now.second
        anchor_hour = anchor.timestamp() - anchor.minute * 60 - anchor.second
        return (current_hour - anchor_hour) // 3_600

    current_date = now.date()
    anchor_date = anchor.date()
    if recurrence == "weekly":
        current_date = current_date.subtract(days=current_date.day_of_week().value - 1)
        anchor_date = anchor_date.subtract(days=anchor_date.day_of_week().value - 1)
        return int(current_date.since(anchor_date, total="days")) // 7

    assert recurrence == "daily"
    return int(current_date.since(anchor_date, total="days"))


def job_period(name: str, job: JobConfig, now: Instant, timezone: str) -> str:
    "Group calendar units from the first attempt into persistent every-N periods"

    local_now = now.to_tz(timezone)
    if job.every == 1:
        return period_key(job.recurrence, local_now)

    # activemodel's last() selects the smallest primary key, including failed first attempts
    first_attempt = JobRun.select().filter_by(job_name=name, recurrence=job.schedule_key).last()
    anchor = local_now if first_attempt is None else Instant.parse_iso(first_attempt.started_at).to_tz(timezone)
    units = calendar_units_since(job.recurrence, local_now, anchor)
    return f"{period_key(job.recurrence, anchor)}:{units // job.every}"


def initialize_database() -> None:
    "Initialize ActiveModel and serialize WAL setup and history table creation"

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_DIRECTORY.mkdir(parents=True, exist_ok=True)
    activemodel.init(
        f"sqlite:///{DATABASE_PATH}",
        engine_options={"connect_args": {"timeout": 30}},
    )

    # serialize first-time schema creation across simultaneous runner invocations
    with SCHEMA_LOCK_PATH.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        engine = activemodel.get_engine()
        # wal persists across connections; verify SQLite accepted the requested mode
        with engine.connect() as connection:
            mode = connection.exec_driver_sql("PRAGMA journal_mode=WAL").scalar_one()
            if mode != "wal":
                raise RuntimeError(f"SQLite did not enable WAL: {mode}")

            connection.commit()

        SQLModel.metadata.create_all(engine)


def acquire_job_lock(lock: TextIO) -> bool:
    "Try an exclusive flock without waiting; log and skip an already owned lock"

    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        if error.errno in (errno.EACCES, errno.EAGAIN):
            log.info("lock unavailable", lock_path=Path(lock.name))
            return False

        raise

    return True


async def tee_output(
    reader: ByteReceiveStream, destination: TextIO | None, chunks: list[bytes]
) -> None:
    "Capture stream bytes and optionally mirror decoded output to the terminal"

    # decode incrementally so multibyte characters can span pipe reads
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    async for chunk in reader:
        # capture bytes before decoding so cancellation cannot lose a partial character
        chunks.append(chunk)
        if destination is None:
            continue

        text = decoder.decode(chunk)
        destination.write(text)
        destination.flush()

    if destination is not None:
        destination.write(decoder.decode(b"", final=True))
        destination.flush()


def kill_process_group(process: Process) -> None:
    # kill the entire job, including shell children that still hold output pipes
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


async def execute_job(run: JobRun, lock: TextIO) -> bool:
    "Execute and tee a job, then kill remaining children and persist its final result"

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    process: Process | None = None
    status = "interrupted"
    exit_code: int | None = None
    started = anyio.current_time()
    command = [SHELL_PATH, "-l", "-o", "NO_INTERACTIVE", "-c", run.command]

    try:
        log.info("job started", job_name=run.job_name, run_id=run.id,
                 timeout_seconds=run.timeout_seconds, command=shlex.join(command),
                 cwd=WORKING_DIRECTORY)
        # finish launch before observing cancellation so cleanup always owns the process
        with anyio.CancelScope(shield=True):
            process = await anyio.open_process(
                command,
                cwd=WORKING_DIRECTORY,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                # inherit the job lock so a surviving command still owns it if the runner dies
                # otherwise a restarted runner could launch a duplicate while that command runs
                # the lock releases once every inherited copy of this descriptor is closed
                # descendants retain it only if they preserve the descriptor when spawning
                pass_fds=(lock.fileno(),),
            )
        assert process.stdout is not None and process.stderr is not None

        with anyio.move_on_after(run.timeout_seconds) as deadline:
            async with anyio.create_task_group() as readers:
                readers.start_soon(tee_output, process.stdout, sys.stdout, stdout_chunks)
                readers.start_soon(tee_output, process.stderr, sys.stderr, stderr_chunks)
                # descendants may keep pipes open after the shell exits
                # keep output draining inside the timeout so inherited pipes cannot hang the job
                # monitor readers alongside the process so stream failures surface immediately
                exit_code = await process.wait()
        if deadline.cancelled_caught:
            status = "timed_out"
        else:
            status = "succeeded" if exit_code == 0 else "failed"
    finally:
        # level cancellation repeats at every await; shield cleanup until history is saved
        with anyio.CancelScope(shield=True):
            if process is not None:
                kill_process_group(process)
                assert process.stdout is not None and process.stderr is not None
                # drain both streams even if one failed, then persist before propagating the error
                # a failed reader can leave a full pipe that blocks process.wait even after kill
                async with anyio.create_task_group() as readers:
                    readers.start_soon(tee_output, process.stdout, None, stdout_chunks)
                    readers.start_soon(tee_output, process.stderr, None, stderr_chunks)
                    exit_code = await process.wait()
                await process.aclose()

            run.status = status
            run.stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace")
            run.stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace")
            run.exit_code = exit_code
            run.finished_at = Instant.now().format_iso()
            run.save()
            log.info("job finished", job_name=run.job_name, run_id=run.id,
                     status=run.status, exit_code=run.exit_code,
                     duration_seconds=round(anyio.current_time() - started, 3))

    return status == "succeeded"


async def run_due_job(
    name: str,
    job: JobConfig,
    timezone: str,
    timeout_seconds: float,
) -> bool:
    "Lock a job, skip a completed period, recover abandoned attempts, and run if due"

    with (LOCK_DIRECTORY / JOB_LOCK_FILENAME.format(name=name)).open("a") as lock:
        if not acquire_job_lock(lock):
            log.info("job skipped", job_name=name, reason="lock unavailable")
            return True

        # only inspect state once this process exclusively owns the job
        now = Instant.now()
        period = job_period(name, job, now, timezone)
        completed = JobRun.select().filter_by(
            job_name=name, recurrence=job.schedule_key, period=period, status="succeeded"
        ).first()
        if completed is not None:
            log.info("job skipped", job_name=name, reason="already succeeded",
                     recurrence=job.schedule_key, period=period)
            return True

        # close the streaming read session before updating the recovered attempts
        abandoned_runs = list(JobRun.select().filter_by(job_name=name, status="running").all())
        # owning the lock proves earlier running rows no longer have a worker
        for abandoned in abandoned_runs:
            abandoned.status = "interrupted"
            abandoned.save()

        run = JobRun(
            job_name=name,
            recurrence=job.schedule_key,
            period=period,
            command=build_job_command(job),
            timeout_seconds=job.timeout_seconds or timeout_seconds,
            started_at=now.format_iso(),
        )
        run.save()
        return await execute_job(run, lock)


async def cancel_on_signal(
    signals: AsyncIterator[int],
    scope: anyio.CancelScope,
    *,
    task_status: TaskStatus[anyio.CancelScope] = anyio.TASK_STATUS_IGNORED,
) -> None:
    "Cancel the job group on a signal; expose a scope to stop this listener"

    with anyio.CancelScope() as listener_scope:
        task_status.started(listener_scope)
        async for stop_signal in signals:
            log.info("shutdown requested", signal=signal.Signals(stop_signal).name)
            scope.cancel()
            return


@asynccontextmanager
async def stop_on_signals() -> AsyncIterator[TaskGroup]:
    "Install stop callbacks for the run's lifetime, including shutdown cleanup"

    with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async with anyio.create_task_group() as group:
            listener_scope = await group.start(cancel_on_signal, signals, group.cancel_scope)
            try:
                yield group
            finally:
                listener_scope.cancel()


async def run_once_job(
    name: str, job: JobConfig, timezone: str, timeout_seconds: float,
    results: list[bool], finished: anyio.Event, job_count: int,
) -> None:
    "Record one job result and wake the caller when every check has finished"

    results.append(await run_due_job(name, job, timezone, timeout_seconds))
    if len(results) == job_count:
        finished.set()


async def run_due_jobs(
    jobs: dict[str, JobConfig],
    timezone: str,
    timeout_seconds: float,
) -> bool:
    "Check each job once, await due jobs, and report whether they all succeeded"

    results: list[bool] = []
    finished = anyio.Event()
    async with stop_on_signals() as group:
        for name, job in jobs.items():
            group.start_soon(run_once_job, name, job, timezone, timeout_seconds,
                             results, finished, len(jobs))
        if jobs:
            await finished.wait()

    return len(results) == len(jobs) and all(results)


async def run_scheduled_job(
    name: str, job: JobConfig, timezone: str, timeout_seconds: float, active: set[str],
) -> None:
    "Release the active marker after a job check, including cancellation cleanup"

    try:
        await run_due_job(name, job, timezone, timeout_seconds)
    finally:
        active.remove(name)


async def run_scheduler(
    jobs: dict[str, JobConfig],
    timezone: str,
    timeout_seconds: float,
    check_interval_seconds: float,
) -> bool:
    "Run periodic checks until a signal or unexpected job error stops the scheduler"

    with SCHEDULER_LOCK_PATH.open("a") as scheduler_lock:
        if not acquire_job_lock(scheduler_lock):
            Console().print("The scheduler is already running for this workspace.", style="yellow")
            return True

        active: set[str] = set()
        # finish subprocess cleanup and history writes before releasing daemon ownership
        async with stop_on_signals() as group:
            # task groups propagate unexpected failures and await subprocess/history cleanup
            while True:
                for name, job in jobs.items():
                    if name in active:
                        log.info("job skipped", job_name=name, reason="already running")
                        continue

                    # dispatch independently so long jobs never delay checks of other jobs
                    active.add(name)
                    group.start_soon(run_scheduled_job, name, job, timezone, timeout_seconds, active)

                # one poll after a delay coalesces missed checks without replaying them
                await anyio.sleep(check_interval_seconds)

    return True


def execute(options: RunnerOptions) -> None:
    "Run the foreground scheduler, or catch up once with --once"

    jobs = load_jobs(options.config)
    Instant.now().to_tz(options.timezone)
    initialize_database()
    mode = "once" if options.once else "scheduler"
    log.info("runner started", mode=mode, timezone=options.timezone, job_count=len(jobs),
             config_path=options.config,
             check_interval_seconds=None if options.once else options.check_interval_seconds)
    try:
        if options.once:
            succeeded = anyio.run(run_due_jobs, jobs, options.timezone, options.timeout_seconds)
        else:
            succeeded = anyio.run(run_scheduler, jobs, options.timezone, options.timeout_seconds,
                                  options.check_interval_seconds)
    finally:
        # emit shutdown only after the task group has drained output and saved history
        log.info("runner stopped", mode=mode)

    raise SystemExit(0 if succeeded else 1)


app = App()


@app.default
def main(*, options: Annotated[RunnerOptions | None, Parameter(name="*")] = None) -> None:
    "Run the foreground scheduler, or catch up once with --once"

    # defer default validation until invocation so help and --config work without cron.yml
    try:
        if options is None:
            options = RunnerOptions()
    except ValidationError as error:
        # model defaults are constructed in the callback, outside Cyclopts' parser
        Console(stderr=True).print(error, style="red", markup=False)
        raise SystemExit(2) from error

    execute(options)


if __name__ == "__main__":
    app()
