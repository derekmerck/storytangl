"""Resolution-oriented helpers for the virtual machine layer."""

from .queries import (
    get_visit_count,
    is_first_visit,
    steps_since_last_visit,
    is_self_loop,
    in_subroutine,
    get_caller_frame,
    get_call_depth,
    get_root_caller,
)
from .traversable import TraversableSubgraph

__all__ = [
    "TraversableSubgraph",
    "get_visit_count",
    "is_first_visit",
    "steps_since_last_visit",
    "is_self_loop",
    "in_subroutine",
    "get_caller_frame",
    "get_call_depth",
    "get_root_caller",
]
