"""Interactive StoryTangl CLI wired through the service manager."""

from __future__ import annotations

import inspect
from uuid import UUID

import cmd2

from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager, build_service_manager


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
        if "user_id" in signature.parameters and "user_id" not in kwargs and self.user_id is not None:
            kwargs["user_id"] = self.user_id
        if "ledger_id" in signature.parameters and "ledger_id" not in kwargs and self.ledger_id is not None:
            kwargs["ledger_id"] = self.ledger_id
        return method(**kwargs)


def create_cli_app() -> StoryTanglCLI:
    """Instantiate the CLI, service manager, and persistence plumbing."""

    persistence = PersistenceManagerFactory.create_persistence_manager()
    service_manager = build_service_manager(persistence)
    return StoryTanglCLI(service_manager=service_manager)


__all__ = ["StoryTanglCLI", "create_cli_app"]
