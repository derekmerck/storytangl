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

from .world import World
from .world_bundle import WorldBundle
from .world_loader import WorldLoader
from .world_manifest import WorldManifest
