from __future__ import annotations

"""Bootstrap helpers for service38 orchestrator and gateway wiring."""

from typing import Any

from .controllers import DEFAULT_CONTROLLERS
from .gateway import ServiceGateway38
from .orchestrator import Orchestrator38


DEFAULT_ENDPOINT_POLICIES: dict[str, dict[str, tuple[str, ...]]] = {
    "RuntimeController.create_story38": {"persist_paths": ("details.ledger",)},
    "UserController.create_user": {"persist_paths": ("details.user",)},
}


def register_default_controllers(orchestrator: Orchestrator38) -> None:
    """Register the standard controller set for service38."""

    for controller in DEFAULT_CONTROLLERS:
        orchestrator.register_controller(controller)


def apply_default_endpoint_policies(orchestrator: Orchestrator38) -> None:
    """Apply built-in persistence policy overrides used by service38."""

    for endpoint_name, policy in DEFAULT_ENDPOINT_POLICIES.items():
        orchestrator.set_endpoint_policy(endpoint_name, **policy)


def build_service_gateway38(
    persistence_manager: Any,
    *,
    default_render_profile: str = "raw",
) -> ServiceGateway38:
    """Build a configured service38 gateway."""

    orchestrator = Orchestrator38(persistence_manager)
    register_default_controllers(orchestrator)
    apply_default_endpoint_policies(orchestrator)
    return ServiceGateway38(orchestrator, default_render_profile=default_render_profile)


__all__ = [
    "DEFAULT_ENDPOINT_POLICIES",
    "apply_default_endpoint_policies",
    "build_service_gateway38",
    "register_default_controllers",
]
