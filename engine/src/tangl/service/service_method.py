"""Lightweight metadata for canonical service-manager methods."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Callable, TypeVar, cast


class ServiceAccess(str, Enum):
    """Access classes for public service methods."""

    PUBLIC = "public"
    CLIENT = "client"
    DEV = "dev"


class ServiceContext(str, Enum):
    """Context requirements for service methods."""

    NONE = "none"
    USER = "user"
    LEDGER = "ledger"
    SESSION = "session"
    WORLD = "world"


class ServiceWriteback(str, Enum):
    """Writeback policy for direct service-manager methods."""

    NONE = "none"
    USER = "user"
    LEDGER = "ledger"
    SESSION = "session"
    EXPLICIT = "explicit"


class BlockingMode(str, Enum):
    """Execution blocking classification for wrappers and transports."""

    SYNC = "sync"
    MAY_BLOCK = "may_block"


@dataclass(frozen=True)
class ServiceMethodSpec:
    """Metadata attached to one canonical service-manager method."""

    name: str
    access: ServiceAccess
    context: ServiceContext
    writeback: ServiceWriteback
    blocking: BlockingMode
    capability: str | None = None
    operation_id: str | None = None

    def with_name(self, name: str) -> "ServiceMethodSpec":
        """Return a copy with the resolved method name."""

        return replace(self, name=name)


ServiceCallable = TypeVar("ServiceCallable", bound=Callable[..., Any])


def service_method(
    *,
    access: ServiceAccess,
    context: ServiceContext,
    writeback: ServiceWriteback,
    blocking: BlockingMode = BlockingMode.SYNC,
    capability: str | None = None,
    operation_id: str | None = None,
) -> Callable[[ServiceCallable], ServiceCallable]:
    """Attach bounded metadata to a canonical service-manager method."""

    def decorator(func: ServiceCallable) -> ServiceCallable:
        spec = ServiceMethodSpec(
            name=func.__name__,
            access=access,
            context=context,
            writeback=writeback,
            blocking=blocking,
            capability=capability,
            operation_id=operation_id,
        )
        setattr(func, "_service_method_spec", spec)
        return func

    return decorator


def get_service_method_spec(func: Callable[..., Any]) -> ServiceMethodSpec | None:
    """Return attached service-method metadata when present."""

    spec = getattr(func, "_service_method_spec", None)
    if isinstance(spec, ServiceMethodSpec):
        return cast(ServiceMethodSpec, spec)
    return None


__all__ = [
    "BlockingMode",
    "ServiceAccess",
    "ServiceContext",
    "ServiceMethodSpec",
    "ServiceWriteback",
    "get_service_method_spec",
    "service_method",
]
