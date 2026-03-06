from __future__ import annotations

"""Bootstrap helpers for service orchestrator and gateway wiring."""

from typing import Any

from .controllers import DEFAULT_CONTROLLERS
from .gateway import ServiceGateway
from .orchestrator import Orchestrator


DEFAULT_ENDPOINT_POLICIES: dict[str, dict[str, tuple[str, ...]]] = {
    "RuntimeController.create_story": {"persist_paths": ("details.ledger",)},
    "UserController.create_user": {"persist_paths": ("details.user",)},
}


def register_default_controllers(orchestrator: Orchestrator) -> None:
    """Register the standard controller set for service."""

    for controller in DEFAULT_CONTROLLERS:
        orchestrator.register_controller(controller)


def apply_default_endpoint_policies(orchestrator: Orchestrator) -> None:
    """Apply built-in persistence policy overrides used by service."""

    for endpoint_name, policy in DEFAULT_ENDPOINT_POLICIES.items():
        orchestrator.set_endpoint_policy(endpoint_name, **policy)


def build_service_gateway(
    persistence_manager: Any,
    *,
    default_render_profile: str = "raw",
) -> ServiceGateway:
    """Build a configured service gateway."""

    orchestrator = Orchestrator(persistence_manager)
    register_default_controllers(orchestrator)
    apply_default_endpoint_policies(orchestrator)
    return ServiceGateway(orchestrator, default_render_profile=default_render_profile)

__all__ = [
    "DEFAULT_ENDPOINT_POLICIES",
    "apply_default_endpoint_policies",
    "build_service_gateway",
    "register_default_controllers",
]
