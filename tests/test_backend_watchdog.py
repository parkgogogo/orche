from __future__ import annotations

import backend


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(seconds, 0.1)


def test_claim_turn_notification_deduplicates_same_event(xdg_runtime):
    backend.save_meta(
        "demo-session",
        {
            "session": "demo-session",
            "pending_turn": {
                "turn_id": "turn-1",
                "notifications": {},
            },
        },
    )

    assert backend.claim_turn_notification("demo-session", "completed", turn_id="turn-1", source="hook") is True
    assert backend.claim_turn_notification("demo-session", "completed", turn_id="turn-1", source="hook") is False


def test_run_session_watchdog_emits_stalled_event(xdg_runtime, monkeypatch):
    clock = FakeClock()
    backend.save_meta(
        "demo-session",
        {
            "session": "demo-session",
            "cwd": "/repo",
            "agent": "codex",
            "pane_id": "%1",
            "pending_turn": {
                "turn_id": "turn-1",
                "prompt": "do the work",
                "before_capture": "",
                "submitted_at": 0.0,
                "pane_id": "%1",
                "notifications": {},
                "watchdog": {
                    "state": "queued",
                    "last_progress_at": 0.0,
                    "last_sample_at": 0.0,
                    "idle_samples": 0,
                    "stop_requested": False,
                },
            },
        },
    )

    samples = [
        {
            "signature": "sig-1",
            "cursor_x": "1",
            "cursor_y": "1",
            "cpu_percent": 0.0,
            "agent_running": True,
            "capture": "working",
        },
        {
            "signature": "sig-1",
            "cursor_x": "1",
            "cursor_y": "1",
            "cpu_percent": 0.0,
            "agent_running": True,
            "capture": "working",
        },
        {
            "signature": "sig-1",
            "cursor_x": "1",
            "cursor_y": "1",
            "cpu_percent": 0.0,
            "agent_running": True,
            "capture": "working",
        },
    ]
    emitted = []

    def fake_sample(session: str, *, pane_id: str = ""):
        index = min(len(emitted) + int(clock.now), len(samples) - 1)
        payload = dict(samples[index])
        payload.setdefault("pane_id", pane_id or "%1")
        payload.setdefault("pane_in_mode", "0")
        payload.setdefault("pane_dead", "0")
        payload.setdefault("pane_current_command", "codex")
        payload.setdefault("capture_bytes", len(str(payload["capture"]).encode("utf-8")))
        payload.setdefault("tail", str(payload["capture"]))
        return payload

    def fake_emit(session: str, *, event: str, summary: str, status: str, turn_id: str = "", cwd: str = "", source: str = ""):
        emitted.append(
            {
                "session": session,
                "event": event,
                "summary": summary,
                "status": status,
                "turn_id": turn_id,
                "cwd": cwd,
                "source": source,
            }
        )
        meta = backend.load_meta(session)
        meta.pop("pending_turn", None)
        backend.save_meta(session, meta)
        return True

    monkeypatch.setattr(backend, "sample_watchdog_state", fake_sample)
    monkeypatch.setattr(backend, "emit_internal_notify", fake_emit)
    monkeypatch.setattr(backend.time, "time", clock.time)
    monkeypatch.setattr(backend.time, "sleep", clock.sleep)

    result = backend.run_session_watchdog(
        "demo-session",
        turn_id="turn-1",
        poll_interval=1.0,
        stalled_after=2.0,
        needs_input_after=10.0,
    )

    assert result == "completed"
    assert emitted == [
        {
            "session": "demo-session",
            "event": "stalled",
            "summary": "working",
            "status": "warning",
            "turn_id": "turn-1",
            "cwd": "/repo",
            "source": "watchdog",
        }
    ]


def test_run_session_watchdog_emits_failed_event_when_agent_exits(xdg_runtime, monkeypatch):
    clock = FakeClock()
    backend.save_meta(
        "demo-session",
        {
            "session": "demo-session",
            "cwd": "/repo",
            "agent": "codex",
            "pane_id": "%1",
            "pending_turn": {
                "turn_id": "turn-2",
                "prompt": "do the work",
                "before_capture": "",
                "submitted_at": 0.0,
                "pane_id": "%1",
                "notifications": {},
                "watchdog": {
                    "state": "queued",
                    "last_progress_at": 0.0,
                    "last_sample_at": 0.0,
                    "idle_samples": 0,
                    "stop_requested": False,
                },
            },
        },
    )

    samples = iter(
        [
            {
                "signature": "sig-1",
                "cursor_x": "1",
                "cursor_y": "1",
                "cpu_percent": 0.0,
                "agent_running": True,
                "capture": "working",
                "pane_id": "%1",
                "pane_in_mode": "0",
                "pane_dead": "0",
                "pane_current_command": "codex",
                "capture_bytes": 7,
                "tail": "working",
            },
            {
                "signature": "sig-1",
                "cursor_x": "1",
                "cursor_y": "1",
                "cpu_percent": 0.0,
                "agent_running": False,
                "capture": "working",
                "pane_id": "%1",
                "pane_in_mode": "0",
                "pane_dead": "1",
                "pane_current_command": "zsh",
                "capture_bytes": 7,
                "tail": "working",
            },
        ]
    )
    emitted = []

    def fake_sample(session: str, *, pane_id: str = ""):
        return dict(next(samples))

    def fake_emit(session: str, *, event: str, summary: str, status: str, turn_id: str = "", cwd: str = "", source: str = ""):
        emitted.append((event, summary, status, turn_id, cwd, source))
        return True

    monkeypatch.setattr(backend, "sample_watchdog_state", fake_sample)
    monkeypatch.setattr(backend, "emit_internal_notify", fake_emit)
    monkeypatch.setattr(backend.time, "time", clock.time)
    monkeypatch.setattr(backend.time, "sleep", clock.sleep)

    result = backend.run_session_watchdog(
        "demo-session",
        turn_id="turn-2",
        poll_interval=1.0,
        stalled_after=30.0,
        needs_input_after=60.0,
    )

    assert result == "failed"
    assert emitted == [
        (
            "failed",
            "working",
            "failure",
            "turn-2",
            "/repo",
            "watchdog",
        )
    ]
