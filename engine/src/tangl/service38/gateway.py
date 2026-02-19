from __future__ import annotations

"""Public service38 gateway for operation-token based execution."""

from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from .api_endpoint import WritebackMode
from .hooks import GatewayHooks
from .operations import ServiceOperation38, endpoint_for_operation, operation_for_endpoint
from .orchestrator import ExecuteOptions, Orchestrator38


@dataclass(frozen=True)
class GatewayExecuteOptions:
    """Optional call overrides for service38 gateway execution."""

    render_profile: str | Iterable[str] | None = "raw"
    writeback_mode: WritebackMode | None = None
    persist_paths: tuple[str, ...] | None = None


class ServiceGateway38:
    """High-level gateway that executes tokenized service operations."""

    def __init__(
        self,
        orchestrator: Orchestrator38,
        *,
        hooks: GatewayHooks | None = None,
        default_render_profile: str = "raw",
    ) -> None:
        self.orchestrator = orchestrator
        self.hooks = hooks or GatewayHooks()
        self.default_render_profile = default_render_profile
        self.hooks.install_default_hooks()

    @property
    def persistence(self) -> Any:
        """Expose orchestrator persistence for transport helpers."""

        return self.orchestrator.persistence

    def execute(
        self,
        operation: ServiceOperation38 | str,
        *,
        user_id: UUID | None = None,
        render_profile: str | Iterable[str] | None = None,
        writeback_mode: WritebackMode | None = None,
        persist_paths: tuple[str, ...] | None = None,
        **params: Any,
    ) -> Any:
        """Execute a service38 operation with per-request render profile."""

        op = operation if isinstance(operation, ServiceOperation38) else ServiceOperation38(operation)
        endpoint_name = endpoint_for_operation(op)
        profile = render_profile if render_profile is not None else self.default_render_profile

        inbound_params = self.hooks.run_inbound(
            dict(params),
            operation=op,
            render_profile=profile,
            user_id=user_id,
        )

        result = self.orchestrator.execute(
            endpoint_name,
            user_id=user_id,
            exec_options=ExecuteOptions(
                writeback_mode=writeback_mode,
                persist_paths=persist_paths,
            ),
            **inbound_params,
        )

        return self.hooks.run_outbound(
            result,
            operation=op,
            render_profile=profile,
            user_id=user_id,
        )

    def execute_endpoint(
        self,
        endpoint_name: str,
        *,
        user_id: UUID | None = None,
        render_profile: str | Iterable[str] | None = None,
        writeback_mode: WritebackMode | None = None,
        persist_paths: tuple[str, ...] | None = None,
        **params: Any,
    ) -> Any:
        """Execute by endpoint name, internally resolving an operation token."""

        try:
            operation = operation_for_endpoint(endpoint_name)
        except KeyError:
            profile = render_profile if render_profile is not None else self.default_render_profile
            result = self.orchestrator.execute(
                endpoint_name,
                user_id=user_id,
                exec_options=ExecuteOptions(
                    writeback_mode=writeback_mode,
                    persist_paths=persist_paths,
                ),
                **dict(params),
            )
            return result if profile == "raw" else self.hooks.run_outbound(
                result,
                operation=ServiceOperation38.SYSTEM_INFO,
                render_profile=profile,
                user_id=user_id,
            )

        return self.execute(
            operation,
            user_id=user_id,
            render_profile=render_profile,
            writeback_mode=writeback_mode,
            persist_paths=persist_paths,
            **params,
        )


__all__ = [
    "GatewayExecuteOptions",
    "ServiceGateway38",
]
