"""Interactive StoryTangl CLI wired through the service orchestrator."""

from __future__ import annotations

from typing import Iterable
from uuid import UUID

import cmd2

from tangl.persistence import PersistenceManagerFactory
from tangl.service import AccessLevel, AuthMode, Orchestrator, ServiceConfig
from tangl.service.controllers import (
    RuntimeController as RuntimeServiceController,
    SystemController as SystemServiceController,
    UserController as UserServiceController,
    WorldController as WorldServiceController,
)

class StoryTanglCLI(cmd2.Cmd):
    """Cmd2 shell that delegates all operations to the orchestrator."""

    prompt = "⅁$ "

    def __init__(
            self,
            orchestrator: Orchestrator,
            *,
            user_id: UUID | None = None,
            ledger_id: UUID | None = None,
            register_controllers: bool = True,
    ) -> None:
        super().__init__(
            allow_cli_args=False,
            auto_load_commands=False,
        )

        self.orchestrator = orchestrator
        self.persistence = orchestrator.persistence
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

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    def set_user(self, user_id: UUID | None) -> None:
        """Update the active user context."""

        self.user_id = user_id

    def set_ledger(self, ledger_id: UUID | None) -> None:
        """Update the active ledger context."""

        self.ledger_id = ledger_id

    def call_endpoint(self, endpoint: str, /, **params) -> object:
        """Execute ``endpoint`` through the orchestrator with implicit context."""

        kwargs = dict(params)
        if "user_id" not in kwargs and self.user_id is not None:
            kwargs["user_id"] = self.user_id
        if "ledger_id" not in kwargs and self.ledger_id is not None:
            kwargs["ledger_id"] = self.ledger_id
        return self.orchestrator.execute(endpoint, **kwargs)

    def remove_resources(self, identifiers: Iterable[UUID]) -> None:
        """Remove resources from persistence when ``drop_user`` returns ids."""

        if self.persistence is None:
            return
        for identifier in identifiers:
            try:
                self.persistence.remove(identifier)
            except KeyError:
                continue


def create_cli_app() -> StoryTanglCLI:
    """Instantiate the CLI, orchestrator, and persistence plumbing."""

    persistence = PersistenceManagerFactory.create_persistence_manager()
    config = ServiceConfig(
        auth_mode=AuthMode.OFF,
        default_user_label="cli",
        default_access_level=AccessLevel.ADMIN,
    )
    orchestrator = Orchestrator(persistence, config=config)
    for controller in (
        RuntimeServiceController,
        UserServiceController,
        SystemServiceController,
        WorldServiceController,
    ):
        orchestrator.register_controller(controller)
    return StoryTanglCLI(orchestrator=orchestrator)


__all__ = ["StoryTanglCLI", "create_cli_app"]
