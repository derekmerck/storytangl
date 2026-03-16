"""Interactive StoryTangl CLI wired through the service gateway."""

from __future__ import annotations

from typing import Any, Iterable
from uuid import UUID

import cmd2

from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceGateway, ServiceOperation, build_service_gateway
from tangl.service.operations import endpoint_for_operation


class StoryTanglCLI(cmd2.Cmd):
    """Cmd2 shell that delegates operations to the service gateway."""

    prompt = "⅁$ "

    def __init__(
        self,
        orchestrator: Any | None = None,
        *,
        service_gateway: ServiceGateway | None = None,
        render_profile: str = "raw",
        user_id: UUID | None = None,
        ledger_id: UUID | None = None,
        register_controllers: bool = True,
    ) -> None:
        super().__init__(
            allow_cli_args=False,
            auto_load_commands=False,
        )

        self.orchestrator = orchestrator
        self.service_gateway = service_gateway
        if service_gateway is not None:
            self.persistence = service_gateway.persistence
        elif orchestrator is not None:
            self.persistence = orchestrator.persistence
        else:
            self.persistence = None
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

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    def set_user(self, user_id: UUID | None) -> None:
        """Update the active user context."""

        self.user_id = user_id

    def set_ledger(self, ledger_id: UUID | None) -> None:
        """Update the active ledger context."""

        self.ledger_id = ledger_id

    def _prepare_context_kwargs(self, params: dict[str, object]) -> dict[str, object]:
        """Inject active user/ledger context unless already supplied."""

        kwargs = dict(params)
        if "user_id" not in kwargs and self.user_id is not None:
            kwargs["user_id"] = self.user_id
        if "ledger_id" not in kwargs and self.ledger_id is not None:
            kwargs["ledger_id"] = self.ledger_id
        return kwargs

    def call_operation(self, operation: ServiceOperation, /, **params) -> object:
        """Execute ``operation`` with explicit per-request render profile."""

        kwargs = self._prepare_context_kwargs(params)

        if self.service_gateway is not None:
            return self.service_gateway.execute(
                operation,
                render_profile=self.render_profile,
                **kwargs,
            )

        if self.orchestrator is None:
            raise RuntimeError("No orchestrator or service gateway configured")

        endpoint = endpoint_for_operation(operation)
        return self.orchestrator.execute(endpoint, **kwargs)

    def call_endpoint(self, endpoint: str, /, **params) -> object:
        """Execute ``endpoint`` directly (legacy helper)."""

        kwargs = self._prepare_context_kwargs(params)
        if self.service_gateway is not None:
            return self.service_gateway.execute_endpoint(
                endpoint,
                render_profile=self.render_profile,
                **kwargs,
            )
        if self.orchestrator is None:
            raise RuntimeError("No orchestrator or service gateway configured")
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
    service_gateway = build_service_gateway(persistence, default_render_profile="raw")
    return StoryTanglCLI(service_gateway=service_gateway)


__all__ = ["StoryTanglCLI", "create_cli_app"]
