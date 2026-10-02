# The Crossroads Inn

**The Crossroads Inn** is the author-facing baseline world. It is deliberately
small and ordinary: enough structure to show what a StoryTangl bundle looks like
without asking the reader to understand a domain mechanic, custom projection, or
adapter at the same time.

Follow a traveler into an inn, meet Aria, take one of several ordinary choices,
and eventually choose a route toward the Northern Pass.

## What it actually demonstrates

- convention-based world discovery through `world.yaml`;
- near-native YAML compilation;
- scenes, blocks, successor actions, and cross-scene references;
- one scene-level `Actor` template;
- optional narrative and avatar media roles;
- ordinary materialization into a playable story graph.

The script currently declares a couple of local values in its opening block,
but does not use them to drive later behavior. This world therefore does **not**
claim stateful consequence as part of its teaching surface.

## Why it stays small

This is the world to copy when the question is “what does a normal StoryTangl
story look like?” Focused mechanics live in sibling worlds; composed game
grammars live in the recipe section of [the worlds catalog](../README.md); codec
and client adapters live in the advanced section.

Keeping those concerns separate makes this directory useful as a starting point
instead of turning it into a museum of every feature the engine has ever grown.

## Bundle structure

```text
reference/
├── world.yaml
├── script.yaml
├── README.md
└── media/
    └── images/
        ├── tavern.svg
        ├── forest.svg
        └── companion.svg
```

See the repository [README](../../README.md) for current install and runtime
commands.
