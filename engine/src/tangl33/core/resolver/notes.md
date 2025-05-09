tangl.core.resolver
===================

Resolution system for matching requirements to suitable providers.

The resolver is the algorithmic heart of StoryTangl's dynamic narrative
generation, implementing a sophisticated matching protocol:

1. Start with a node's requirements
2. Search for matching providers in increasingly broader scopes
3. For each scope, check all providers against requirement criteria
4. When a match is found, create any necessary graph connections
5. If no match exists, attempt dynamic creation through strategies

This process embodies the "quantum collapse" of the story space, where
potential story elements only become concrete when needed by the
current narrative path.

The resolution system balances performance (searching local scopes first)
with flexibility (falling back to broader scopes and creation).
