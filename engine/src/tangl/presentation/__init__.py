"""Domain-neutral syntax clients may render or solicit.

Presentation values are advisory. They do not authorize actions, render a
widget tree, own transport, or establish narrative truth.
"""

from .geometry import NormalizedRect
from .hints import PresentationHints, StagingHints
from .events import GrammarHint, GrammarNoun, GrammarVerb, UxEvent
from .intent import (
    Accepts,
    Blocker,
    CostPreview,
    UIHints,
)
from .surface import HasSurface, Surface, SurfaceSlot
from .values import KvRow, PrimitiveValue
from .dispatch import (
    on_advertise_story_info_channels,
    on_advertise_world_info_channels,
    on_get_story_info,
    presentation_dispatch,
)
from .projection import (
    BadgeListValue,
    BrandingValue,
    InfoAffordance,
    InfoState,
    ItemListValue,
    KvListValue,
    ProjectedItem,
    ProjectedSection,
    ProjectedState,
    ScalarValue,
    SectionValue,
    ProjectionRequest,
    TableValue,
    ThemeTokens,
)

__all__ = [
    "Accepts",
    "BadgeListValue",
    "BrandingValue",
    "Blocker",
    "CostPreview",
    "GrammarHint",
    "GrammarNoun",
    "GrammarVerb",
    "HasSurface",
    "InfoAffordance",
    "InfoState",
    "ItemListValue",
    "KvListValue",
    "KvRow",
    "NormalizedRect",
    "PresentationHints",
    "PrimitiveValue",
    "ProjectedItem",
    "ProjectedSection",
    "ProjectedState",
    "ProjectionRequest",
    "ScalarValue",
    "SectionValue",
    "StagingHints",
    "Surface",
    "SurfaceSlot",
    "TableValue",
    "ThemeTokens",
    "UIHints",
    "UxEvent",
    "on_advertise_story_info_channels",
    "on_advertise_world_info_channels",
    "on_get_story_info",
    "presentation_dispatch",
]
