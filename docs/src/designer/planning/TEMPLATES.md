# Template System

## Overview
Templates are reusable blueprints for creating actors, locations, and other narrative
entities. They are stored as immutable :class:`Record` objects inside
``World.template_registry`` once a world is instantiated.

**Content-addressable records.** Templates inherit from
:class:`tangl.core.content_addressable.ContentAddressable`. Each template therefore
exposes a ``content_hash`` that captures the structure of the template while ignoring
metadata such as ``label`` or ``scope``. Identical structures have the same hash,
allowing the registry to deduplicate entries, audit provenance, and perform content-based
queries.

```python
template = world.find_template("generic_guard")
template.content_hash  # raw bytes suitable for registry lookups
template.get_content_identifier()  # 16-char hex string for logs and receipts
```

Use the hash when emitting receipts or proving which template created an entity. Fields
like ``obj_cls``, ``archetype``, ``conditions``, and ``effects`` influence the hash,
while metadata fields (``label``, ``scope``, ``template_names``) do not.

## Declaration Levels
Templates can be declared at three levels. The world registry records where a template
originated via the optional :class:`ScopeSelector` metadata.

> **Note:** Story materialization now uses address-based templates directly. Legacy
> ``scenes``/``blocks`` structures are treated as a compatibility format and can be
> converted into hierarchical templates (see
> ``tangl.loaders.legacy.scene_block_importer.SceneBlockImporter``).

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
