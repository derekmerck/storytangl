# Exception Policy

The service layer raises :class:`~tangl.service.exceptions.ServiceError` subclasses
for expected failure modes. The orchestrator converts them into
``RuntimeInfo(status="error", code=..., message=...)`` objects so transports can
present consistent error payloads.

- Use :class:`AccessDeniedError` when authentication or authorization fails.
- Use :class:`ResourceNotFoundError` when a referenced ledger, user, or world
  cannot be located.
- Use :class:`InvalidOperationError` when the request conflicts with the current
  state (e.g., resolving an unavailable choice).
- Use :class:`ValidationError` for input problems that pass basic type coercion
  but violate business rules.
- Use :class:`NoActiveStoryError` when the user has no active ledger and the
  orchestrator cannot infer one.

Other exception types (``ValueError``, ``TypeError``, etc.) signal unexpected
bugs and should propagate. They appear as tracebacks in CLI contexts and become
HTTP 500 responses in REST.

## Usage

```python
from tangl.service.exceptions import InvalidOperationError

def resolve_choice(choice_id: UUID, available: set[UUID]) -> None:
    if choice_id not in available:
        raise InvalidOperationError(f"Choice {choice_id} not available")
```

## Transport mappings

- The orchestrator wraps ``ServiceError`` instances as ``RuntimeInfo`` errors and
  includes cursor metadata when available.
- FastAPI exception handlers (``tangl.rest.api_server``) map ``ServiceError``
  subclasses to HTTP 400/403/404/422 responses while preserving the ``code``
  field in the JSON payload.

Exceptions allow early exit and keep controllers focused on domain logic while
transports handle presentation.
