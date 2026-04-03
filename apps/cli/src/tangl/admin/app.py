"""One-shot admin and remote utility commands built on Typer."""

from typing import Annotated
from uuid import UUID

import typer
import yaml

from tangl.service import build_service_manager


app = typer.Typer(
    help="Backend and remote service utilities that complement the interactive story shell.",
    no_args_is_help=True,
)


BackendOption = Annotated[
    str | None,
    typer.Option(help="Manager backend override: local or remote."),
]
ApiUrlOption = Annotated[
    str | None,
    typer.Option(help="Remote REST API root."),
]
ApiKeyOption = Annotated[
    str | None,
    typer.Option(help="Bound API key for remote protected calls."),
]
SecretOption = Annotated[
    str | None,
    typer.Option(help="Secret that can be resolved to an API key."),
]
TimeoutOption = Annotated[
    float | None,
    typer.Option(help="Remote request timeout in seconds."),
]


def _print_payload(value: object) -> None:
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="python")
    elif isinstance(value, list):
        payload = [
            item.model_dump(mode="python") if hasattr(item, "model_dump") else item
            for item in value
        ]
    else:
        payload = value
    typer.echo(yaml.dump(payload, indent=2, sort_keys=False))


def _build_manager(
    *,
    backend: str | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
    secret: str | None = None,
    timeout_s: float | None = None,
):
    return build_service_manager(
        backend=backend,
        api_url=api_url,
        api_key=api_key,
        secret=secret,
        timeout_s=timeout_s,
    )


def _fail(exc: Exception) -> typer.Exit:
    typer.echo(f"[FAIL] {exc}", err=True)
    return typer.Exit(code=1)


@app.command("system-info")
def system_info(
    backend: BackendOption = None,
    api_url: ApiUrlOption = None,
    api_key: ApiKeyOption = None,
    secret: SecretOption = None,
    timeout_s: TimeoutOption = None,
) -> None:
    """Print high-level system information."""

    try:
        info = _build_manager(
            backend=backend,
            api_url=api_url,
            api_key=api_key,
            secret=secret,
            timeout_s=timeout_s,
        ).get_system_info()
    except Exception as exc:  # noqa: BLE001
        raise _fail(exc) from exc
    _print_payload(info)


@app.command("worlds")
def worlds(
    backend: BackendOption = None,
    api_url: ApiUrlOption = None,
    api_key: ApiKeyOption = None,
    secret: SecretOption = None,
    timeout_s: TimeoutOption = None,
) -> None:
    """List available worlds through the current manager backend."""

    try:
        info = _build_manager(
            backend=backend,
            api_url=api_url,
            api_key=api_key,
            secret=secret,
            timeout_s=timeout_s,
        ).list_worlds()
    except Exception as exc:  # noqa: BLE001
        raise _fail(exc) from exc
    _print_payload(info)


@app.command("world-info")
def world_info(
    world_id: str = typer.Argument(..., help="World identifier to inspect."),
    backend: BackendOption = None,
    api_url: ApiUrlOption = None,
    api_key: ApiKeyOption = None,
    secret: SecretOption = None,
    timeout_s: TimeoutOption = None,
) -> None:
    """Print metadata for one world."""

    try:
        info = _build_manager(
            backend=backend,
            api_url=api_url,
            api_key=api_key,
            secret=secret,
            timeout_s=timeout_s,
        ).get_world_info(world_id=world_id)
    except Exception as exc:  # noqa: BLE001
        raise _fail(exc) from exc
    _print_payload(info)


@app.command("create-user")
def create_user(
    user_secret: str = typer.Argument(..., help="Secret used to create a new user."),
    backend: BackendOption = None,
    api_url: ApiUrlOption = None,
    api_key: ApiKeyOption = None,
    secret: SecretOption = None,
    timeout_s: TimeoutOption = None,
) -> None:
    """Create one user and print the resulting runtime info."""

    try:
        info = _build_manager(
            backend=backend,
            api_url=api_url,
            api_key=api_key,
            secret=secret,
            timeout_s=timeout_s,
        ).create_user(secret=user_secret)
    except Exception as exc:  # noqa: BLE001
        raise _fail(exc) from exc
    _print_payload(info)


@app.command("user-info")
def user_info(
    user_id: UUID = typer.Argument(..., help="User identifier to inspect."),
    backend: BackendOption = None,
    api_url: ApiUrlOption = None,
    api_key: ApiKeyOption = None,
    secret: SecretOption = None,
    timeout_s: TimeoutOption = None,
) -> None:
    """Print metadata for one user."""

    try:
        info = _build_manager(
            backend=backend,
            api_url=api_url,
            api_key=api_key,
            secret=secret,
            timeout_s=timeout_s,
        ).get_user_info(user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        raise _fail(exc) from exc
    _print_payload(info)


@app.command("key-for-secret")
def key_for_secret(
    user_secret: str = typer.Argument(..., help="Secret to encode as an API key."),
    backend: BackendOption = None,
    api_url: ApiUrlOption = None,
    api_key: ApiKeyOption = None,
    secret: SecretOption = None,
    timeout_s: TimeoutOption = None,
) -> None:
    """Resolve one secret to an API key through the service surface."""

    try:
        info = _build_manager(
            backend=backend,
            api_url=api_url,
            api_key=api_key,
            secret=secret,
            timeout_s=timeout_s,
        ).get_key_for_secret(secret=user_secret)
    except Exception as exc:  # noqa: BLE001
        raise _fail(exc) from exc
    _print_payload(info)


def run() -> None:
    """Execute the Typer app as a console entry point."""

    app()


if __name__ == "__main__":
    run()
