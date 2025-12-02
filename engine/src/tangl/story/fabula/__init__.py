"""
## tangl.fabula

The fabula is the latent, unrealized space of all possible stories.

The `World` is discrete fabula representation.  It manages story templates, custom classes, assets, and resources.

## Creation

```python
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World

# From YAML file
sm = ScriptManager.from_file("story.yaml")
world = World(label="my_world", script_manager=sm)

# From dict
sm = ScriptManager.from_data(data)
world = World(label="my_world", script_manager=sm)
```

## Methods

### create_story(story_label: str, mode: str = 'full') -> StoryGraph

Create a new story instance.

**Parameters**:
- `story_label`: Unique identifier for this story instance
- `mode`: Materialization mode ('full', 'hybrid', 'lazy')

**Returns**: Graph ready for navigation. Inspect ``graph.initial_cursor_id`` for the
starting node identifier.

**Example**:
```python
story = world.create_story(user=player_1)
start_node = story.get(story.initial_cursor_id)
```

### Managers

- `world.script_manager`: Access story templates
- `world.domain_manager`: Register custom classes
- `world.asset_manager`: Manage game assets
- `world.resource_manager`: Manage media files
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .asset_manager import AssetManager
from .domain_manager import DomainManager
from .script_manager import ScriptManager
from .world import World

if TYPE_CHECKING:  # pragma: no cover - import side effects only for typing
    from tangl.loaders.bundle import WorldBundle
    from tangl.loaders.manifest import WorldManifest
    from .world_loader import WorldLoader

__all__ = [
    "AssetManager",
    "DomainManager",
    "ScriptManager",
    "World",
    "WorldBundle",
    "WorldLoader",
    "WorldManifest",
]


def __getattr__(name: str):
    if name == "WorldBundle":
        from tangl.loaders.bundle import WorldBundle as Bundle

        return Bundle
    if name == "WorldManifest":
        from tangl.loaders.manifest import WorldManifest as Manifest

        return Manifest
    if name == "WorldLoader":
        from .world_loader import WorldLoader as Loader

        return Loader
    raise AttributeError(name)
