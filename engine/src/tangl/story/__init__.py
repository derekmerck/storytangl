"""Legacy compatibility shim that re-exports ``tangl.story38``."""

import os

import tangl.story38 as _story38

from tangl.story38 import *  # noqa: F401,F403
from tangl.story38 import Action as _Story38Action
from tangl.story38 import Block as _Story38Block
from tangl.story38 import Scene as _Story38Scene
from tangl.story38 import StoryGraph38 as _StoryGraph38
from tangl.story.episode.action import Action as _LegacyAction
from tangl.story.episode.block import Block as _LegacyBlock
from tangl.story.episode.menu_block import MenuBlock as _LegacyMenuBlock
from tangl.story.episode.scene import Scene as _LegacyScene
from tangl.story.story_graph import StoryGraph as _LegacyStoryGraph


_V38_VALUES = {"1", "true", "yes", "on", "v38", "new"}
_LEGACY_VALUES = {"0", "false", "no", "off", "legacy", "old"}


def _pick(symbol: str, legacy_value, v38_value, *, default: str = "v38"):
    raw_value = os.getenv(
        f"TANGL_SHIM_STORY_{symbol}",
        os.getenv("TANGL_SHIM_STORY_DEFAULT", default),
    )
    selected = str(raw_value).strip().lower()
    if selected in _LEGACY_VALUES:
        return legacy_value
    if selected in _V38_VALUES:
        return v38_value
    raise ValueError(
        f"Invalid shim value '{raw_value}' for TANGL_SHIM_STORY_{symbol}. "
        f"Use one of {sorted(_LEGACY_VALUES | _V38_VALUES)}."
    )


# Preserve legacy episode primitives on the top-level ``tangl.story`` surface.
Action = _pick("ACTION", _LegacyAction, _Story38Action)
Block = _pick("BLOCK", _LegacyBlock, _Story38Block)
MenuBlock = _LegacyMenuBlock
Scene = _pick("SCENE", _LegacyScene, _Story38Scene)
StoryGraph = _pick("STORYGRAPH", _LegacyStoryGraph, _StoryGraph38, default="v38")
LegacyStoryGraph = _LegacyStoryGraph

__all__ = getattr(
    _story38,
    "__all__",
    [name for name in dir(_story38) if not name.startswith("_")],
)

for name in ("Action", "Block", "LegacyStoryGraph", "MenuBlock", "Scene", "StoryGraph"):
    if name not in __all__:
        __all__.append(name)
