"""Interactive StoryTangl CLI wired through the service manager."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from uuid import UUID

import cmd2

from tangl.info import __version__
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager, build_service_manager

from .rendering import create_terminal_renderer

_SPLASH_PATH = Path(__file__).with_name("assets") / "splash.txt"


class StoryTanglCLI(cmd2.Cmd):
    """Cmd2 shell that delegates commands to the canonical service manager."""

    prompt = "⅁$ "

    def __init__(
        self,
        *,
        service_manager: ServiceManager | None = None,
        render_profile: str = "raw",
        user_id: UUID | None = None,
        ledger_id: UUID | None = None,
        terminal_style: str = "plain",
        register_controllers: bool = True,
    ) -> None:
        super().__init__(
            allow_cli_args=False,
            auto_load_commands=False,
        )

        self.service_manager = service_manager
        self.persistence = service_manager.persistence if service_manager is not None else None
        self.render_profile = render_profile
        self.user_id = user_id
        self.ledger_id = ledger_id
        self.terminal_style = terminal_style
        self.terminal_renderer = create_terminal_renderer(terminal_style)
        self.intro = _load_splash_text()

        if register_controllers:
            self._register_controllers()

    def _register_controllers(self) -> None:
        """Register all available CLI command sets explicitly."""

        from .controllers.dev_controller import DevController
        from .controllers.story_controller import StoryController
        from .controllers.system_controller import SystemController
        from .controllers.user_controller import UserController
        from .controllers.world_controller import WorldController

        for controller_cls in (
            StoryController,
            UserController,
            WorldController,
            SystemController,
            DevController,
        ):
            self.register_command_set(controller_cls())

    def set_user(self, user_id: UUID | None) -> None:
        """Update the active user context."""

        self.user_id = user_id

    def set_ledger(self, ledger_id: UUID | None) -> None:
        """Update the active ledger context."""

        self.ledger_id = ledger_id

    def call_service(self, method_name: str, /, **params: object) -> object:
        """Execute one canonical service-manager method."""

        if self.service_manager is None:
            raise RuntimeError("No service manager configured")

        method = getattr(self.service_manager, method_name)
        signature = inspect.signature(method)
        kwargs = dict(params)
        if (
            "user_id" in signature.parameters
            and "user_id" not in kwargs
            and self.user_id is not None
        ):
            kwargs["user_id"] = self.user_id
        if (
            "ledger_id" in signature.parameters
            and "ledger_id" not in kwargs
            and self.ledger_id is not None
        ):
            kwargs["ledger_id"] = self.ledger_id
        return method(**kwargs)

    def emit_terminal(self, renderables: list[object]) -> None:
        """Write renderer output through the active terminal renderer."""

        self.terminal_renderer.emit(self, renderables)


def create_cli_app(*, terminal_style: str = "plain") -> StoryTanglCLI:
    """Instantiate the CLI, service manager, and persistence plumbing."""

    persistence = PersistenceManagerFactory.create_persistence_manager()
    service_manager = build_service_manager(persistence)
    return StoryTanglCLI(service_manager=service_manager, terminal_style=terminal_style)


def _load_splash_text() -> str | None:
    if not _SPLASH_PATH.exists():
        return None
    return _format_splash_text(_SPLASH_PATH.read_text(encoding="utf-8")).rstrip()


def _format_splash_text(template: str) -> str:
    display_version = _major_minor_version(__version__)
    return template.replace("{version_line}", _splash_version_line(template, display_version))


def _major_minor_version(version: str) -> str:
    match = re.match(r"^(\d+)\.(\d+)", version)
    if match is None:
        return version
    return f"{match.group(1)}.{match.group(2)}"


def _splash_version_line(template: str, version: str) -> str:
    top_border = next(
        (line for line in template.splitlines() if "╭" in line and "╮" in line),
        None,
    )
    if top_border is None:
        return f"StoryTan⅁l v{version}"

    box_start = top_border.index("╭")
    box_end = top_border.index("╮")
    indent = top_border[:box_start]
    interior_width = box_end - box_start - 1
    left_content = "   StoryTan⅁l"
    version_text = f"v{version}"
    right_padding = 10
    spacing = max(1, interior_width - len(left_content) - len(version_text) - right_padding)
    right_padding = max(1, interior_width - len(left_content) - spacing - len(version_text))
    return f"{indent}│{left_content}{' ' * spacing}{version_text}{' ' * right_padding}│"


__all__ = ["StoryTanglCLI", "create_cli_app"]
