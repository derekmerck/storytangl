# Core

Game entities are built up from multiple layers.

## Node

The core {class}`.Node` class provides basic protocols for id, attribute organization, variable namespaces, and self-structuring.  {class}`.NodeIndex` provides metadata and node collection indices.

```{eval-rst}
.. automodule:: tangl.core.node
.. automodule:: tangl.core.node_index
```

## Service Mixins

Core mixins provide service protocols: {class}`.Renderable` for text and media generation, {class}`.Traversable` for narrative structure, {class}`Conditions <.Conditional>` and {class}`Effects <.Applyable>`.

```{eval-rst}
.. automodule:: tangl.core.renderable
.. automodule:: tangl.core.traversable
.. automodule:: tangl.core.runtime
```


