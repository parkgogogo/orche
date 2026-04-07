from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import cli
from cli import app


def test_update_command_reports_success(xdg_runtime, monkeypatch):
    runner = CliRunner()
    captured: dict[str, object] = {}

    class Result:
        version = "v9.9.9"
        target = "linux-x64"
        link_path = Path("/tmp/orche")
        updated = True

    monkeypatch.setattr(
        cli,
        "perform_self_update",
        lambda **kwargs: captured.update(kwargs) or Result(),
    )

    result = runner.invoke(app, ["update", "--version", "v9.9.9"])

    assert result.exit_code == 0
    assert captured == {"requested_version": "v9.9.9"}
    assert "update ok: version=v9.9.9" in result.output
    assert "updated=yes" in result.output
