tangl.core.provision
====================

Provider implementations that satisfy declared requirements.

The provision system forms the bridge between requirements and 
their fulfillment through:

- ResourceProvider: A capability that advertises provider keys
- Template: A factory for dynamically creating providers
- Provision strategies: Algorithms for matching and creation

This implements the "provider" side of StoryTangl's architecture,
where narrative elements can be materialized on demand when they're
needed by the storyline.

The provision system enables emergent narratives where the exact
set of characters, locations, and objects is determined by the
path taken through the story, not predefined.

See Also
--------
resolver: System for matching requirements to providers  
Requirement: The declaration of needed resources
