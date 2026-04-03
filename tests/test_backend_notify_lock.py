from __future__ import annotations

import threading
import time

import pytest

import backend


def test_deliver_notify_to_session_types_and_submits(monkeypatch):
    actions = []

    monkeypatch.setattr(backend, "bridge_resolve", lambda session: "%42" if session == "target-session" else None)
    monkeypatch.setattr(backend, "bridge_type", lambda session, text: actions.append(("type", session, text)))
    monkeypatch.setattr(backend, "bridge_keys", lambda session, keys: actions.append(("keys", session, list(keys))))

    pane_id = backend.deliver_notify_to_session("target-session", "hello")

    assert pane_id == "%42"
    assert actions == [
        ("type", "target-session", "hello"),
        ("keys", "target-session", ["Enter"]),
    ]


def test_deliver_notify_to_session_requires_existing_target(monkeypatch):
    monkeypatch.setattr(backend, "bridge_resolve", lambda session: None)

    with pytest.raises(backend.OrcheError, match="notify target session not found: missing-session"):
        backend.deliver_notify_to_session("missing-session", "hello")


def test_deliver_notify_to_session_serializes_same_target_session(xdg_runtime, monkeypatch):
    sequence = []
    start_barrier = threading.Barrier(3)

    monkeypatch.setattr(backend, "bridge_resolve", lambda session: "%42")

    def fake_bridge_type(session, text):
        sequence.append(f"type:{text}")
        time.sleep(0.15)

    def fake_bridge_keys(session, keys):
        sequence.append(f"keys:{keys[0].lower()}")

    monkeypatch.setattr(backend, "bridge_type", fake_bridge_type)
    monkeypatch.setattr(backend, "bridge_keys", fake_bridge_keys)

    errors = []

    def worker(text):
        try:
            start_barrier.wait()
            backend.deliver_notify_to_session("shared-target", text)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    first = threading.Thread(target=worker, args=("first",))
    second = threading.Thread(target=worker, args=("second",))
    first.start()
    second.start()
    start_barrier.wait()
    first.join()
    second.join()

    assert errors == []
    assert sequence in (
        ["type:first", "keys:enter", "type:second", "keys:enter"],
        ["type:second", "keys:enter", "type:first", "keys:enter"],
    )


def test_deliver_notify_to_session_allows_parallel_writes_to_different_targets(xdg_runtime, monkeypatch):
    intervals = []
    start_barrier = threading.Barrier(3)
    interval_lock = threading.Lock()

    monkeypatch.setattr(backend, "bridge_resolve", lambda session: "%42")

    def fake_bridge_type(session, text):
        started = time.time()
        time.sleep(0.15)
        ended = time.time()
        with interval_lock:
            intervals.append((session, started, ended))

    monkeypatch.setattr(backend, "bridge_type", fake_bridge_type)
    monkeypatch.setattr(backend, "bridge_keys", lambda session, keys: None)

    def worker(session_name, text):
        start_barrier.wait()
        backend.deliver_notify_to_session(session_name, text)

    first = threading.Thread(target=worker, args=("target-a", "first"))
    second = threading.Thread(target=worker, args=("target-b", "second"))
    first.start()
    second.start()
    start_barrier.wait()
    first.join()
    second.join()

    assert len(intervals) == 2
    latest_start = max(start for _session, start, _end in intervals)
    earliest_end = min(end for _session, _start, end in intervals)
    assert latest_start < earliest_end
