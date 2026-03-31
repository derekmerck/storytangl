"""Tests for the Typer-based admin utility."""

from __future__ import annotations

import importlib
from uuid import uuid4

from typer.testing import CliRunner

from tangl.service.response import RuntimeInfo, SystemInfo, UserSecret, WorldInfo

from tangl.admin.app import app as admin_app


admin_module = importlib.import_module("tangl.admin.app")


runner = CliRunner()


class FakeManager:
    """Small fake manager for admin command tests."""

    def get_system_info(self) -> SystemInfo:
        return SystemInfo(
            engine="StoryTangl",
            version="3.7.2",
            uptime="a moment",
            worlds=1,
            num_users=2,
        )

    def list_worlds(self) -> list[WorldInfo]:
        return [WorldInfo(label="demo_world", title="Demo World", author="Tests")]

    def get_world_info(self, *, world_id: str) -> WorldInfo:
        return WorldInfo(label=world_id, title="Demo World", author="Tests")

    def create_user(self, *, secret: str) -> RuntimeInfo:
        return RuntimeInfo.ok(message="User created", user_id=str(uuid4()))

    def get_user_info(self, *, user_id):
        raise AssertionError(f"unexpected user_info lookup for {user_id}")

    def get_key_for_secret(self, *, secret: str) -> UserSecret:
        return UserSecret(api_key=f"key:{secret}", user_secret=secret)


def test_system_info_command_renders_yaml(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_builder(**kwargs):
        captured.update(kwargs)
        return FakeManager()

    monkeypatch.setattr(admin_module, "build_service_manager", _fake_builder)

    result = runner.invoke(
        admin_app,
        [
            "system-info",
            "--backend",
            "remote",
            "--api-url",
            "http://127.0.0.1:8000/api/v2",
            "--secret",
            "remote-secret",
        ],
    )

    assert result.exit_code == 0
    assert "StoryTangl" in result.stdout
    assert captured == {
        "backend": "remote",
        "api_url": "http://127.0.0.1:8000/api/v2",
        "api_key": None,
        "secret": "remote-secret",
        "timeout_s": None,
    }


def test_create_user_command_renders_runtime_info(monkeypatch) -> None:
    monkeypatch.setattr(admin_module, "build_service_manager", lambda **_: FakeManager())

    result = runner.invoke(admin_app, ["create-user", "open-sesame"])

    assert result.exit_code == 0
    assert "status: ok" in result.stdout
    assert "message: User created" in result.stdout


def test_worlds_command_lists_worlds(monkeypatch) -> None:
    monkeypatch.setattr(admin_module, "build_service_manager", lambda **_: FakeManager())

    result = runner.invoke(admin_app, ["worlds"])

    assert result.exit_code == 0
    assert "demo_world" in result.stdout
    assert "Demo World" in result.stdout


def test_key_for_secret_command_renders_key(monkeypatch) -> None:
    monkeypatch.setattr(admin_module, "build_service_manager", lambda **_: FakeManager())

    result = runner.invoke(admin_app, ["key-for-secret", "open-sesame"])

    assert result.exit_code == 0
    assert "key:open-sesame" in result.stdout
