"""Domain-neutral syntax clients may render or solicit.

Presentation values are advisory. They do not authorize actions, render a
widget tree, own transport, or establish narrative truth.
"""

from .hints import PresentationHints, StagingHints
from .intent import (
    Accepts,
    Blocker,
    CostPreview,
    UIHints,
)
from .values import KvRow, PrimitiveValue

__all__ = [
    "Accepts",
    "Blocker",
    "CostPreview",
    "KvRow",
    "PresentationHints",
    "PrimitiveValue",
    "StagingHints",
    "UIHints",
]
