# Story

{class}`.StoryNode` and {class}`.Story` respectively extend the core {class}`.Node` and {class}`.Index` classes.

## StoryNode

```{eval-rst}
.. automodule:: tangl.story.story_node
```

StoryNodes have additional specialized protocols layered in for story management.

There are several types of story nodes:
- {class}`Scenes <.Scene>` (narrative containers)
- {class}`Actors <.Actor>` (npcs, dynamic entities)
- {class}`Places <.Place>` (locations, dynamic entities)
- {class}`Assets <.Asset>` (props, tokens, units, static singleton entities).

Within each subtype, further element specializations are available:
- Scene blocks may be {class}`.Activity` menus or {class}`Challenge <.Challenge>` games.  
- Roles may be {class}`.Extras` (generated actors).  
- Assets may be {class}`Commodities <.Commodity>` (fungible assets) or {class}`Units <.Unit>` (game token assets).

Moreover, each _game world_ can have its own story subclasses with additional world-specific features.

### Scenes

```{eval-rst}
.. automodule:: tangl.story.scene.scene
.. automodule:: tangl.story.scene.block
.. automodule:: tangl.story.scene.action
.. automodule:: tangl.story.scene.challenge
.. automodule:: tangl.story.scene.activity
```

### Actors

```{eval-rst}
.. automodule:: tangl.story.actor.actor
.. automodule:: tangl.story.actor.role
.. automodule:: tangl.story.actor.extras
```

See also the {class}`.Avatar` class for dynamically generated svg actor images.

### Places

```{eval-rst}
.. automodule:: tangl.story.place.place
.. automodule:: tangl.story.place.location
```

### Assets

Assets are anything that can be possessed or assigned to another node.  Fungibles are stored in a "wallet" object.  Non-fungibles can be assigned to inventories.  Asset-place and -role hybrids may be assigned to location and role slots.

```{eval-rst}
.. automodule:: tangl.story.asset
```
{##}
{#### Commodity#}
{##}
{#```{eval-rst}#}
{#.. autoclass:: tangl.story.asset.Commodity#}
{#.. autoclass:: tangl.story.asset.ChattelMixin#}
{#.. autoclass:: tangl.story.asset.Wallet#}
{#```#}
{##}
{#### Wearable#}
{##}
{#```{eval-rst}#}
{#.. autoclass:: tangl.story.asset.Wearable#}
{#```#}
{##}
{#### Unit#}
{##}
{#```{eval-rst}#}
{#.. autoclass:: tangl.story.asset.Unit#}
{#.. autoclass:: tangl.story.asset.Squad#}
{#```#}

```{include} storynode_lifecycle.md
```

## Story Index

```{eval-rst}
.. automodule:: tangl.story.story
```

```{include} story_lifecycle.md
```
