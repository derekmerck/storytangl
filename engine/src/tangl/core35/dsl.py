from typing import Callable

from .context import Context

def compile_pred(expr: str) -> Callable[[Context], bool]:
    if expr.strip().lower() in {"true", ""}:
        return lambda ctx: True
    if expr.strip().lower() == "false":
        return lambda ctx: False
    raise ValueError(f"Unsupported predicate: {expr!r}")
