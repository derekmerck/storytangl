"""Remote CLI smoke tests against a live temporary REST server."""

from __future__ import annotations

import io
import socket
import threading
import time
from pathlib import Path

import pytest
import requests
import uvicorn
import yaml

from tangl.cli.app import StoryTanglCLI as TanglShell, create_cli_app
from tangl.config import settings
from tangl.rest.app import app as rest_app
from tangl.rest.dependencies import reset_service_state_for_testing
from tangl.rest.dependencies_gateway import get_service_manager, reset_service_manager_for_testing
from tangl.story.fabula.world import World


LINEAR_SCRIPT = (
    Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "linear_script.yaml"
)


def _capture_output(app: TanglShell) -> str:
    output = app.stdout.getvalue()
    app.stdout.truncate(0)
    app.stdout.seek(0)
    return output


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str, *, timeout_s: float = 5.0) -> None:
    deadline = time.time() + timeout_s
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/system/info", timeout=0.2)
            if response.status_code == 200:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(0.05)

    raise RuntimeError(f"Timed out waiting for test server at {base_url}") from last_error


@pytest.fixture(autouse=True)
def _reset_worlds() -> None:
    World.clear_instances()
    yield
    World.clear_instances()


@pytest.fixture()
def remote_linear_story_server() -> str:
    original_backend = settings.get("service.manager.backend")
    original_remote_api_url = settings.get("service.remote.api_url")
    original_remote_api_key = settings.get("service.remote.api_key")
    original_remote_secret = settings.get("service.remote.secret")
    original_remote_timeout = settings.get("service.remote.timeout_s")

    settings.set("service.manager.backend", "local")
    settings.set("service.remote.api_url", "")
    settings.set("service.remote.api_key", "")
    settings.set("service.remote.secret", "")
    settings.set("service.remote.timeout_s", 5.0)

    reset_service_state_for_testing()
    reset_service_manager_for_testing()

    service_manager = get_service_manager()
    script_data = yaml.safe_load(LINEAR_SCRIPT.read_text(encoding="utf-8"))
    service_manager.load_world(script_data=script_data)

    port = _free_local_port()
    base_url = f"http://127.0.0.1:{port}/api/v2"

    config = uvicorn.Config(
        app=rest_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_for_server(base_url)

    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        if thread.is_alive():
            server.force_exit = True
            thread.join(timeout=5)

        reset_service_manager_for_testing()
        reset_service_state_for_testing()
        settings.set("service.manager.backend", original_backend)
        settings.set("service.remote.api_url", original_remote_api_url)
        settings.set("service.remote.api_key", original_remote_api_key)
        settings.set("service.remote.secret", original_remote_secret)
        settings.set("service.remote.timeout_s", original_remote_timeout)


def test_remote_cli_walkthrough_against_live_server(
    remote_linear_story_server: str,
) -> None:
    unique_secret = "remote-cli-smoke-secret"
    settings.set("service.manager.backend", "remote")
    settings.set("service.remote.api_url", remote_linear_story_server)
    settings.set("service.remote.api_key", "")
    settings.set("service.remote.secret", "")
    settings.set("service.remote.timeout_s", 5.0)

    app = create_cli_app()
    app.stdout = io.StringIO()

    app.onecmd(f"create_user {unique_secret}")
    create_output = _capture_output(app)
    assert "User created with secret" in create_output
    assert app.user_id is not None

    app.onecmd("create_story the_path")
    created_story = _capture_output(app)
    assert "Created story:" in created_story
    assert "You begin your journey at dawn." in created_story
    assert "1. Continue" in created_story

    app.onecmd("story")
    first_update = _capture_output(app)
    assert "Story Update:" in first_update
    assert "You begin your journey at dawn." in first_update
    assert "1. Continue" in first_update

    app.onecmd("do 1")
    second_step = _capture_output(app)
    assert "The path winds through ancient woods." in second_step
    assert "Choices:" in second_step

    app.onecmd("do 1")
    final_step = _capture_output(app)
    assert "You arrive at the village." in final_step
    assert "No available choices." in final_step
