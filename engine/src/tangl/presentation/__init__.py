"""Domain-neutral syntax clients may render or solicit.

Presentation values are advisory. They do not authorize actions, render a
widget tree, own transport, or establish narrative truth.
"""

from .hints import PresentationHints, StagingHints
from .events import GrammarHint, GrammarNoun, GrammarVerb, UxEvent
from .intent import (
    Accepts,
    Blocker,
    CostPreview,
    UIHints,
)
from .values import KvRow, PrimitiveValue
from .projection import (
    BadgeListValue,
    InfoAffordance,
    InfoState,
    ItemListValue,
    KvListValue,
    ProjectedItem,
    ProjectedSection,
    ProjectedState,
    ScalarValue,
    SectionValue,
    StoryInfoRequest,
    TableValue,
)

__all__ = [
    "Accepts",
    "Blocker",
    "BadgeListValue",
    "CostPreview",
    "GrammarHint",
    "GrammarNoun",
    "GrammarVerb",
    "InfoAffordance",
    "InfoState",
    "ItemListValue",
    "KvListValue",
    "KvRow",
    "PresentationHints",
    "PrimitiveValue",
    "ProjectedItem",
    "ProjectedSection",
    "ProjectedState",
    "ScalarValue",
    "SectionValue",
    "StagingHints",
    "StoryInfoRequest",
    "TableValue",
    "UIHints",
    "UxEvent",
]
