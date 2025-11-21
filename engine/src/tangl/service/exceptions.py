"""Service-layer exceptions mapped to native runtime responses."""

from __future__ import annotations


class ServiceError(Exception):
    """Base for service-layer errors that surface as ``RuntimeInfo`` errors."""

    code: str = "SERVICE_ERROR"

    def __init__(self, *args: object):
        super().__init__(*args)


class ResourceNotFoundError(ServiceError):
    """Requested resource (user, ledger, choice, etc.) does not exist."""

    code = "NOT_FOUND"


class InvalidOperationError(ServiceError):
    """Operation is not valid in the current state."""

    code = "INVALID_OPERATION"


class AccessDeniedError(ServiceError):
    """User lacks permission for the requested operation."""

    code = "ACCESS_DENIED"


class ValidationError(ServiceError):
    """Input validation failed for the request."""

    code = "VALIDATION_ERROR"
