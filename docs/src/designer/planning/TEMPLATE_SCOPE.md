# Template Scope

## Overview
Templates can be constrained to specific parts of your story using the `scope` field. This prevents templates from being used in inappropriate contexts.

## Scope Levels

### Global (No Scope)
Templates without scope constraints are available everywhere.

```yaml
templates:
  generic_guard:
    obj_cls: Actor
    # No scope = global
```

### Scene-Scoped (parent_label)
Templates declared in a scene are automatically scoped to that scene's blocks.

```yaml
scenes:
  village:
    templates:
      village_elder:
        obj_cls: Actor
        # Inferred: scope.parent_label = "village"
    
    blocks:
      square:
        roles:
          elder: {actor_template_ref: "village_elder"}  # ✓ In scope
  
  city:
    blocks:
      plaza:
        roles:
          elder: {actor_template_ref: "village_elder"}  # ✗ Out of scope!
```

### Block-Scoped (source_label)
Templates declared in a block are only available in that specific block.

```yaml
scenes:
  lab:
    blocks:
      containment:
        templates:
          specialist:
            obj_cls: Actor
            # Inferred: scope.source_label = "lab.containment"
        
        roles:
          expert: {actor_template_ref: "specialist"}  # ✓ In scope
      
      research:
        roles:
          expert: {actor_template_ref: "specialist"}  # ✗ Out of scope!
```

## Scope Override

You can explicitly override the inferred scope:

```yaml
scenes:
  village:
    templates:
      wandering_merchant:
        obj_cls: Actor
        scope: null  # Override to global (available everywhere)
      
      secret_contact:
        obj_cls: Actor
        scope:
          ancestor_tags: ["conspiracy"]  # Only in blocks with conspiracy tag
```

## Scope Selectors

### source_label
Template only valid in exact source node:

```yaml
scope:
  source_label: "village.smithy"
  # Only works in the "smithy" block of "village" scene
```

### parent_label  
Template valid in children of parent:

```yaml
scope:
  parent_label: "village"
  # Works in any block under "village" scene
```

### ancestor_tags
Template valid if ancestor has matching tags:

```yaml
scope:
  ancestor_tags: ["conspiracy", "hidden"]
  # Works in any block/scene with conspiracy AND hidden in ancestor chain
```

### ancestor_labels
Template valid if ancestor has matching label:

```yaml
scope:
  ancestor_labels: ["village", "city"]
  # Works in blocks under scenes labeled "village" OR "city"
```

## Provisioning Behavior

When a role/setting references a template:

1. **Template lookup:** Find template in `world.template_registry` by label
2. **Scope check:** Validate template is in scope for source node
3. **Instantiation:** If valid, create concrete node from template
4. **Rejection:** If out of scope, log warning and return no offers

## Best Practices

1. **Use global templates for truly generic concepts**
   ```yaml
   templates:
     generic_guard: {...}  # Works everywhere
   ```

2. **Use scene templates for location-specific variants**
   ```yaml
   scenes:
     castle:
       templates:
         royal_guard: {...}  # Only in castle
   ```

3. **Use block templates for ultra-specific needs**
   ```yaml
   blocks:
     throne_room:
       templates:
         king_guard: {...}  # Only here
   ```

4. **Override scope when sharing across scenes**
   ```yaml
   scenes:
     village:
       templates:
         merchant:
           scope: null  # Share with other scenes
   ```

## Troubleshooting

**"Template 'X' not found"**
- Template doesn't exist in registry
- Check spelling and declaration location

**"Template 'X' out of scope"**
- Template has scope constraint not satisfied
- Check scope.parent_label, source_label, etc
- Consider overriding scope to null for global access

**"No offers for requirement"**
- Template exists but is out of scope
- Check debug logs for scope rejection reason
