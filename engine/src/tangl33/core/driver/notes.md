tangl.core.driver
=================

Traversal controller implementing the phased graph exploration protocol.

The cursor system drives StoryTangl's narrative progression through:

- CursorDriver: The coordinator of phased traversal

This component embodies the "observer" role in StoryTangl's quantum 
narrative metaphor, collapsing the story potential into a specific path.

The cursor's strict phase protocol ensures that narrative events occur 
in a predictable, deterministic order while maintaining extensibility
through capability injection.

Phase execution order and services invoked:

- GATHER: context services only
- RESOLVE: builder, gate, before choice, before effect services
- GATE: gating services
- RENDER: render services only
- FINALIZE: after effect, after choice services


