tangl.core.service.provision
============================

Provider implementations that satisfy declared requirements.

The provision system forms the bridge between requirements and 
their fulfillment through:

- ProviderCapability: A capability that advertises provider keys for the PROVIDER service
- Template: A factory for dynamically creating providers
- Provision strategies: Algorithms for _matching_ and _creation_
- resolve_requirements: Core algorithm for satisfying satisfy open requirements on a node

This implements the "provider" side of StoryTangl's architecture,
where narrative elements can be materialized on demand when they're
needed by the storyline.

The provision system enables emergent narratives where the exact
set of characters, locations, and objects is determined by the
path taken through the story, not predefined.

See Also
--------
Capability: Base class for the ProviderCap
Requirement: The declaration of needed resources
