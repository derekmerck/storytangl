tangl.core.context
==================

Contextual data gathering across nested narrative scopes.

The context system implements StoryTangl's variable scoping mechanism,
where information is collected from multiple sources in a principled way:

- Node-local variables (immediate scope)
- Ancestor chain (inheritance scope)
- Graph-wide globals (shared story scope)
- Domain-wide defaults (world rules)

This implementation uses ChainMap for efficient layered access,
and provides a clear protocol for how information shadows across
scope boundaries.

StringMap gathering occurs at the beginning of traversal,
establishing the environment in which all subsequent phase
decisions (redirects, rendering, etc.) will operate.

See Also
--------
ContextHandler: Capability for providing context layers
gather: Core algorithm for context assembly
