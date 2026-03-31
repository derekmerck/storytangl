from __future__ import annotations

"""Bootstrap helpers for the canonical manager-first service wiring."""

from tangl.config import settings
from tangl.persistence import PersistenceManager, PersistenceManagerFactory

from .exceptions import ValidationError
from .remote_service_manager import RemoteServiceManager
from .service_manager import ServiceManager


def build_service_manager(
    persistence_manager: PersistenceManager | None = None,
    *,
    backend: str | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
    secret: str | None = None,
    timeout_s: float | None = None,
) -> ServiceManager:
    """Build the canonical explicit service manager."""

    configured_backend = backend or getattr(
        getattr(settings.service, "manager", None),
        "backend",
        "local",
    )
    normalized_backend = str(configured_backend).strip().lower()

    if normalized_backend == "remote":
        remote_settings = getattr(settings.service, "remote", None)
        resolved_api_url = api_url
        if resolved_api_url is None and remote_settings is not None:
            resolved_api_url = getattr(remote_settings, "api_url", None)
        resolved_api_key = api_key
        if resolved_api_key is None and remote_settings is not None:
            resolved_api_key = getattr(remote_settings, "api_key", None)
        resolved_secret = secret
        if resolved_secret is None and remote_settings is not None:
            resolved_secret = getattr(remote_settings, "secret", None)
        resolved_timeout = timeout_s
        if resolved_timeout is None and remote_settings is not None:
            resolved_timeout = getattr(remote_settings, "timeout_s", 5.0)
        if resolved_api_url is None or not str(resolved_api_url).strip():
            raise ValidationError("Remote service manager requires service.remote.api_url")

        return RemoteServiceManager(
            str(resolved_api_url),
            persistence_manager=persistence_manager,
            api_key=str(resolved_api_key) if resolved_api_key is not None else None,
            secret=str(resolved_secret) if resolved_secret is not None else None,
            timeout_s=float(resolved_timeout) if resolved_timeout is not None else 5.0,
        )

    if normalized_backend != "local":
        raise ValidationError(f"Unknown service manager backend: {configured_backend}")

    if persistence_manager is None:
        persistence_manager = PersistenceManagerFactory.create_persistence_manager()
    return ServiceManager(persistence_manager)

__all__ = ["build_service_manager"]
