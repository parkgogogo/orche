from __future__ import annotations

import threading

import pytest

import backend
from agents import claude as claude_agent
from agents import codex as codex_agent
from agents import common as common_agent
from paths import locks_dir


@pytest.mark.parametrize(
    ("lock_factory", "path_factory"),
    [
        pytest.param(
            lambda: backend.session_lock("demo/session", timeout=0.2),
            lambda: backend.lock_path("demo/session"),
            id="session_lock",
        ),
        pytest.param(
            lambda: backend.target_session_io_lock("notify/session", timeout=0.2),
            lambda: backend.notify_target_lock_path("notify/session"),
            id="target_session_io_lock",
        ),
        pytest.param(
            lambda: backend.inline_host_lock(backend.tmux_session_name("inline/session"), "%9", timeout=0.2),
            lambda: backend.inline_host_lock_path(backend.tmux_session_name("inline/session"), "%9"),
            id="inline_host_lock",
        ),
        pytest.param(
            lambda: codex_agent.source_config_lock(timeout=0.2),
            lambda: locks_dir() / f"{codex_agent.SOURCE_CONFIG_LOCK_NAME}.lock",
            id="codex_source_config_lock",
        ),
        pytest.param(
            lambda: claude_agent.source_config_lock(timeout=0.2),
            lambda: locks_dir() / f"{claude_agent.SOURCE_CONFIG_LOCK_NAME}.lock",
            id="claude_source_config_lock",
        ),
    ],
)
def test_shared_locks_tolerate_stale_files_and_reuse_paths(xdg_runtime, lock_factory, path_factory):
    path = path_factory()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stale\n", encoding="utf-8")

    with lock_factory():
        assert path.exists()

    assert path.exists()

    with lock_factory():
        assert path.exists()


def test_session_lock_preserves_timeout_error_when_contended(xdg_runtime):
    acquired = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with backend.session_lock("held/session", timeout=0.2):
            acquired.set()
            release.wait(timeout=1.0)

    thread = threading.Thread(target=holder)
    thread.start()
    assert acquired.wait(timeout=1.0)

    with pytest.raises(backend.OrcheError, match="Timed out waiting for session lock: held/session"):
        with backend.session_lock("held/session", timeout=0.05):
            pass

    release.set()
    thread.join(timeout=1.0)
    assert not thread.is_alive()


def test_session_storage_key_avoids_collisions_across_paths_and_runtime_names(tmp_path, monkeypatch):
    first = "demo/a"
    second = "demo-a"

    first_key = common_agent.session_storage_key(first)
    second_key = common_agent.session_storage_key(second)

    monkeypatch.setattr(codex_agent, "DEFAULT_RUNTIME_HOME_ROOT", tmp_path / "codex-home")
    monkeypatch.setattr(claude_agent, "DEFAULT_RUNTIME_HOME_ROOT", tmp_path / "claude-home")

    assert first_key.startswith("demo-a-")
    assert second_key.startswith("demo-a-")
    assert first_key != second_key
    assert backend.session_key(first) == first_key
    assert backend.session_key(second) == second_key
    assert backend.history_path(first).name == f"{first_key}.jsonl"
    assert backend.meta_path(first).name == f"{first_key}.json"
    assert backend.lock_path(first).name == f"{first_key}.lock"
    assert backend.notify_target_lock_path(first).name == f"{first_key}.notify.lock"
    assert backend.history_path(first) != backend.history_path(second)
    assert backend.meta_path(first) != backend.meta_path(second)
    assert backend.lock_path(first) != backend.lock_path(second)
    assert backend.notify_target_lock_path(first) != backend.notify_target_lock_path(second)
    assert backend.tmux_session_name(first) == f"{backend.TMUX_SESSION}-{first_key}"
    assert backend.tmux_session_name(first) != backend.tmux_session_name(second)
    assert backend.inline_host_lock_path(backend.tmux_session_name(first), "%1") != backend.inline_host_lock_path(
        backend.tmux_session_name(second),
        "%1",
    )
    assert codex_agent.default_codex_home_path(first) == (tmp_path / "codex-home" / f"orche-codex-{first_key}")
    assert claude_agent.default_claude_home_path(first) == (tmp_path / "claude-home" / f"orche-claude-{first_key}")
    assert codex_agent.default_codex_home_path(first) != codex_agent.default_codex_home_path(second)
    assert claude_agent.default_claude_home_path(first) != claude_agent.default_claude_home_path(second)
