# Template System

## Overview
Templates are reusable blueprints for creating actors, locations, and other narrative
entities. They are stored as immutable :class:`Record` objects inside
``World.template_registry`` once a world is instantiated.

## Declaration Levels
Templates can be declared at three levels. The world registry records where a template
originated via the optional :class:`ScopeSelector` metadata.

### World Level (Global)
```yaml
label: my_world
metadata:
  title: Example World
  author: StoryTangl
templates:
  generic_guard:
    obj_cls: tangl.story.concepts.actor.actor.Actor
    archetype: guard
```

### Scene Level (Parent Scope)
```yaml
scenes:
  village:
    label: village
    blocks: {}
    templates:
      village_elder:
        obj_cls: tangl.story.concepts.actor.actor.Actor
```

### Block Level (Source Scope)
```yaml
scenes:
  village:
    label: village
    blocks:
      smithy:
        label: village.smithy
        templates:
          apprentice:
            obj_cls: tangl.story.concepts.actor.actor.Actor
```

### Explicit Scope Overrides
Set ``scope`` directly inside the template payload to override inference. Use ``null`` for
fully global templates declared inside nested scopes.

```yaml
scenes:
  village:
    label: village
    blocks: {}
    templates:
      traveling_merchant:
        obj_cls: tangl.story.concepts.actor.actor.Actor
        scope: null  # remains global instead of inheriting parent_label
```

## Querying Templates
```python
world = World(label="example", script_manager=manager)

# By label
template = world.find_template("generic_guard")

# By type
actors = world.actor_templates
locations = world.location_templates

# By criteria
guards = world.template_registry.find_all(
    is_instance=ActorScript,
    has_tags={"npc"},
    archetype="guard",
)
```

## Duplicate Labels
If multiple templates resolve to the same sanitized label, the world keeps the first entry
and logs a warning for subsequent duplicates. Use unique labels when authoring content to
avoid ambiguity.
