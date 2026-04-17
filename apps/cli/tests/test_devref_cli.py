"""Tests for the Typer-based devref utility."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from tangl.devref.cli import app as devref_app


runner = CliRunner()


def test_build_and_status_commands_render_yaml(tmp_path) -> None:
    db_path = tmp_path / "devref.sqlite3"

    build_result = runner.invoke(devref_app, ["build", "--db", str(db_path), "--full"])
    status_result = runner.invoke(devref_app, ["status", "--db", str(db_path)])

    assert build_result.exit_code == 0
    assert status_result.exit_code == 0
    assert "built: true" in status_result.output
    assert "artifacts:" in status_result.output


def test_status_does_not_create_or_fake_an_unbuilt_database(tmp_path) -> None:
    db_path = tmp_path / "never_built.sqlite3"

    result = runner.invoke(devref_app, ["status", "--db", str(db_path), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["exists"] is False
    assert payload["has_schema"] is False
    assert payload["built"] is False
    assert payload["state"] == "missing"
    assert not db_path.exists()


def test_find_command_renders_json(tmp_path) -> None:
    db_path = tmp_path / "devref.sqlite3"
    runner.invoke(devref_app, ["build", "--db", str(db_path), "--full"])

    result = runner.invoke(
        devref_app,
        ["find", "entity", "--db", str(db_path), "--format", "json", "--limit", "5"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["topics"][0]["topic_id"] == "entity"


def test_pack_command_applies_facet_filter(tmp_path) -> None:
    db_path = tmp_path / "devref.sqlite3"
    runner.invoke(devref_app, ["build", "--db", str(db_path), "--full"])

    result = runner.invoke(
        devref_app,
        ["pack", "phase_ctx", "--db", str(db_path), "--facet", "tests", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["items"]
    assert {item["facet"] for item in payload["items"]} == {"tests"}
