"""Runtime world management.

## tangl.fabula

The fabula is the latent, unrealized space of all possible stories. Worlds are
their discrete runtime representation, bundling templates, domain classes,
assets, and media resources.

## Creation

Service discovery with the :class:`~tangl.service.world_registry.WorldRegistry`
is the preferred entry point:

```python
from tangl.service.world_registry import WorldRegistry

registry = WorldRegistry()
world = registry.get_world("my_world")
```

Tests can compile worlds directly from bundles when mocking discovery:

```python
from pathlib import Path

from tangl.loaders import WorldBundle, WorldCompiler

bundle = WorldBundle.load(Path("tests/worlds/my_world"))
compiler = WorldCompiler()
world = compiler.compile(bundle)
```
"""

from __future__ import annotations

from .asset_manager import AssetManager
from .domain_manager import DomainManager
from .script_manager import ScriptManager
from .world import World

__all__ = [
    "AssetManager",
    "DomainManager",
    "ScriptManager",
    "World",
]
