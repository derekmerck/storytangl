tangl.core.cursor
=================

Traversal controller implementing the phased graph exploration protocol.

The cursor system drives StoryTangl's narrative progression through:

- CursorDriver: The coordinator of phased traversal
- Specialized handlers: Redirection, effects, continuation
- Journal integration: Recording the traversal results

This component embodies the "observer" role in StoryTangl's quantum 
narrative metaphor, collapsing the story potential into a specific path.

The cursor's strict phase protocol ensures that narrative events occur 
in a predictable, deterministic order while maintaining extensibility
through capability injection.

See Also
--------
redirect_handler, effect_handler, continue_handler: 
    Specialized capability factories for cursor phases
