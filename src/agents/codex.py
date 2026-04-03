from __future__ import annotations

import contextlib
import json
import re
import shlex
import shutil
import time
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib
    except ModuleNotFoundError:  # pragma: no cover
        tomllib = None

from paths import ensure_directories, locks_dir

from .base import AgentPlugin, AgentRuntime
from .common import (
    DEFAULT_RUNTIME_HOME_ROOT,
    normalize_runtime_home,
    remove_runtime_home,
    session_key,
    validate_discord_channel_id,
    write_notify_hook,
    write_text_atomically,
)


READY_SURFACE_HINTS = (
    "OpenAI Codex",
    "Approvals:",
    "model:",
    "full-auto",
    "dangerously-bypass-approvals-and-sandbox",
    "Esc to interrupt",
    "Ctrl-C to interrupt",
)
DEFAULT_CODEX_SOURCE_HOME = Path.home() / ".codex"
MANAGED_CODEX_RUNTIME_DIRS = {".tmp", "log", "shell_snapshots", "tmp"}
MANAGED_CODEX_RUNTIME_FILE_GLOBS = ("history.jsonl", "logs_*.sqlite*", "state_*.sqlite*")
TOML_TABLE_HEADER_RE = re.compile(r"^\s*\[\[?.*\]\]?\s*$")
TOML_NOTIFY_KEY_RE = re.compile(r"^\s*notify\s*=")
TOML_PROJECT_HEADER_RE = re.compile(r"^\s*\[projects\.(.+)\]\s*$")
TOML_TRUST_LEVEL_RE = re.compile(r"^\s*trust_level\s*=")
SOURCE_CONFIG_LOCK_NAME = "codex-source-config"
SOURCE_CONFIG_BACKUP_SUFFIX = ".orche.bak"


def default_codex_home_path(session: str) -> Path:
    return DEFAULT_RUNTIME_HOME_ROOT / f"orche-codex-{session_key(session)}"


def default_notify_hook_path(codex_home: Path) -> Path:
    return codex_home / "hooks" / "discord-turn-notify.sh"


def source_codex_config_path() -> Path:
    return DEFAULT_CODEX_SOURCE_HOME / "config.toml"


def source_codex_config_backup_path() -> Path:
    return source_codex_config_path().with_name(source_codex_config_path().name + SOURCE_CONFIG_BACKUP_SUFFIX)


def render_notify_command(hook_path: Path, *, session: str, discord_channel_id: str | None) -> str:
    values = ["/bin/bash", str(hook_path), "--session", session]
    if discord_channel_id:
        values.extend(["--channel-id", validate_discord_channel_id(discord_channel_id)])
    return "notify = [" + ", ".join(json.dumps(value) for value in values) + "]"


def strip_notify_assignments(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    skipping = False
    bracket_depth = 0
    for line in lines:
        if not skipping and TOML_NOTIFY_KEY_RE.match(line):
            skipping = True
            bracket_depth = line.count("[") - line.count("]")
            if bracket_depth <= 0:
                skipping = False
            continue
        if skipping:
            bracket_depth += line.count("[") - line.count("]")
            if bracket_depth <= 0:
                skipping = False
            continue
        cleaned.append(line)
    return cleaned


def read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def validate_toml_document(content: str, *, label: str) -> None:
    if tomllib is None:
        return
    try:
        tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        raise RuntimeError(f"Refusing to write invalid TOML for {label}: {exc}") from exc


def _project_header_path(line: str) -> str | None:
    match = TOML_PROJECT_HEADER_RE.match(line)
    if match is None:
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, str) else None


def render_project_trust_block(cwd: Path) -> str:
    return f"[projects.{json.dumps(str(cwd.resolve()))}]\ntrust_level = \"trusted\"\n"


def upsert_project_trust(content: str, cwd: Path) -> str:
    target = str(cwd.resolve())
    lines = content.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if _project_header_path(line) != target:
            continue
        section_end = index + 1
        while section_end < len(lines) and not TOML_TABLE_HEADER_RE.match(lines[section_end]):
            section_end += 1
        for trust_index in range(index + 1, section_end):
            if not TOML_TRUST_LEVEL_RE.match(lines[trust_index]):
                continue
            replacement = 'trust_level = "trusted"\n'
            if lines[trust_index] == replacement:
                return content
            lines[trust_index] = replacement
            return "".join(lines)
        lines.insert(section_end, 'trust_level = "trusted"\n')
        return "".join(lines)
    updated = content
    if updated and not updated.endswith("\n"):
        updated += "\n"
    if updated.strip():
        updated += "\n"
    updated += render_project_trust_block(cwd)
    return updated


def upsert_top_level_notify(content: str, notify_line: str) -> str:
    lines = strip_notify_assignments(content.splitlines(keepends=True))
    first_table_index = next((index for index, line in enumerate(lines) if TOML_TABLE_HEADER_RE.match(line)), len(lines))
    prefix = lines[:first_table_index]
    suffix = lines[first_table_index:]
    while prefix and not prefix[-1].strip():
        prefix.pop()
    while suffix and not suffix[0].strip():
        suffix.pop(0)
    updated: list[str] = list(prefix)
    if updated and not updated[-1].endswith("\n"):
        updated[-1] += "\n"
    if updated:
        updated.append("\n")
    updated.append(notify_line + "\n")
    if suffix:
        updated.append("\n")
        updated.extend(suffix)
    return "".join(updated)


@contextlib.contextmanager
def source_config_lock(*, timeout: float = 5.0):
    ensure_directories()
    path = locks_dir() / f"{SOURCE_CONFIG_LOCK_NAME}.lock"
    deadline = time.time() + timeout
    while True:
        try:
            fd = path.open("x")
            break
        except FileExistsError:
            if time.time() > deadline:
                raise RuntimeError("Timed out waiting for Codex source config lock")
            time.sleep(0.1)
    try:
        fd.write(str(Path.cwd()))
        fd.flush()
        yield
    finally:
        fd.close()
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


def sync_trust_to_source_config(cwd: Path) -> str:
    config_path = source_codex_config_path()
    with source_config_lock():
        original = read_text_or_empty(config_path)
        if original:
            validate_toml_document(original, label=str(config_path))
        updated = upsert_project_trust(original, cwd)
        if updated != original:
            validate_toml_document(updated, label=str(config_path))
            write_text_atomically(
                config_path,
                updated,
                backup_path=source_codex_config_backup_path(),
            )
        return updated


def prune_managed_codex_home(codex_home: Path) -> None:
    for name in MANAGED_CODEX_RUNTIME_DIRS:
        shutil.rmtree(codex_home / name, ignore_errors=True)
    for pattern in MANAGED_CODEX_RUNTIME_FILE_GLOBS:
        for path in codex_home.glob(pattern):
            with contextlib.suppress(OSError):
                path.unlink()


def rewrite_codex_config(
    codex_home: Path,
    *,
    session: str,
    cwd: Path,
    discord_channel_id: str | None,
) -> None:
    config_toml_path = codex_home / "config.toml"
    base_content = sync_trust_to_source_config(cwd)
    notify_line = render_notify_command(
        default_notify_hook_path(codex_home),
        session=session,
        discord_channel_id=discord_channel_id,
    )
    updated = upsert_top_level_notify(base_content, notify_line)
    validate_toml_document(updated, label=str(config_toml_path))
    write_text_atomically(config_toml_path, updated)


class CodexAgent(AgentPlugin):
    name = "codex"
    display_name = "Codex"
    runtime_label = "CODEX_HOME"
    login_prompts = ("Login with ChatGPT", "Please login")

    def ensure_managed_runtime(
        self,
        session: str,
        *,
        cwd: Path,
        discord_channel_id: str | None,
    ) -> AgentRuntime:
        target = default_codex_home_path(session)
        if not target.exists():
            if DEFAULT_CODEX_SOURCE_HOME.exists():
                shutil.copytree(DEFAULT_CODEX_SOURCE_HOME, target)
            else:
                target.mkdir(parents=True, exist_ok=True)
        prune_managed_codex_home(target)
        write_notify_hook(default_notify_hook_path(target))
        rewrite_codex_config(target, session=session, cwd=cwd, discord_channel_id=discord_channel_id)
        return AgentRuntime(home=str(target.resolve()), managed=True, label=self.runtime_label)

    def build_launch_command(
        self,
        *,
        cwd: Path,
        runtime: AgentRuntime,
        session: str,
        discord_channel_id: str | None,
        approve_all: bool,
    ) -> str:
        _ = approve_all
        prefix = [f"cd {shlex.quote(str(cwd))}"]
        normalized_runtime_home = normalize_runtime_home(runtime.home)
        if normalized_runtime_home:
            prefix.append(f"mkdir -p {shlex.quote(normalized_runtime_home)}")
            prefix.append(f"export CODEX_HOME={shlex.quote(normalized_runtime_home)}")
        if session:
            prefix.append(f"export ORCHE_SESSION={shlex.quote(session)}")
        if discord_channel_id:
            prefix.append(f"export ORCHE_DISCORD_CHANNEL_ID={shlex.quote(validate_discord_channel_id(discord_channel_id))}")
        command = ["codex", "--no-alt-screen", "-C", str(cwd), "--dangerously-bypass-approvals-and-sandbox"]
        prefix.append(f"exec {' '.join(shlex.quote(part) for part in command)}")
        return " && ".join(prefix)

    def matches_process(self, pane_command: str, descendant_commands: list[str]) -> bool:
        if pane_command == "codex":
            return True
        for proc in descendant_commands:
            lowered = proc.lower()
            if "codex" in lowered or "@openai/codex" in lowered:
                return True
        return False

    def capture_has_ready_surface(self, capture: str, cwd: Path) -> bool:
        lowered = capture.lower()
        has_brand = "openai codex" in lowered or "\ncodex" in lowered or " codex" in lowered
        has_context = str(cwd) in capture or any(hint.lower() in lowered for hint in READY_SURFACE_HINTS)
        return has_brand and has_context

    def cleanup_runtime(self, runtime: AgentRuntime) -> None:
        if runtime.home:
            remove_runtime_home(runtime.home)


PLUGINS = [CodexAgent()]
