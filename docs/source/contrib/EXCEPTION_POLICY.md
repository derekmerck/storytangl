# Exception Policy

**ServiceError subclasses**: Become RuntimeInfo(status="error", code=..., message=...)
- Used for expected failure modes (not found, invalid state, etc.)
- CLI catches and displays nicely
- REST maps to appropriate HTTP status + RuntimeInfo body

**Other exceptions**: True bugs/unexpected conditions
- ValueError, TypeError, etc. from bad code
- CLI lets them bubble (traceback helps debug)
- REST catches as 500 + generic error RuntimeInfo

## Usage

```python
# In controller
if choice_id not in available:
    raise InvalidOperationError(f"Choice {choice_id} not available")

# NOT this:
if choice_id not in available:
    return RuntimeInfo(status="error", code="INVALID_CHOICE", ...)
```

## Rationale

Exceptions allow early exit and cleaner control flow. The orchestrator and
transport layers decide how to present them to users.
