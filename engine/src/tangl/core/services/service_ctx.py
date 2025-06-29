from contextlib import contextmanager
from contextvars import ContextVar
from typing import Mapping, Any, Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import _CTX_SVC
    from .predicate import _PRED_SVC
    from .rendering import _RENDER_SVC
    from .effect import _EFFECT_SVC

@contextmanager
def service_ctx(overrides: Mapping[ContextVar[Any], Any]) -> Iterator[None]:
    """
    Temporarily sets multiple ContextVar service channels at once.

    Example
    -------
    >>> with service_ctx({
    ...         _PRED_SVC: lambda ent, ctx: True,                 # stub predicate
    ...         _CTX_SVC : lambda ent: {"foo": "bar"},            # stub context
    ... }):
    ...     resolver.advance_cursor(edge)
    """
    # Set every override and remember their tokens
    if any([not isinstance(var, ContextVar) for var in overrides.keys()]):
        raise ValueError("override keys must be ContextVar")
    tokens = {var: var.set(val) for var, val in overrides.items()}
    try:
        yield
    finally:
        # Always restore original values, even if an exception bubbles up
        for var, tok in tokens.items():
            var.reset(tok)
