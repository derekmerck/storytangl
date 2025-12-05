## MenuBlock: Dynamic Choice Hubs

MenuBlock extends Block to automatically provision choices from compatible blocks.

### Use Cases

- **Location menus**: "You're at the mall. Where to?"
- **Scene selection**: "Which chapter would you like to visit?"
- **Quest boards**: "Available quests" (with conditional availability)
- **Context menus**: Actions based on current world state

### Patterns

**Pull Pattern (Dependencies)**
Menu declares what it wants via `selection_criteria`:

```python
lobby = MenuBlock(
    label="mall_lobby",
    selection_criteria={'has_tags': {'mall_shop'}},
)

# These match and become menu options
clothing = Block(label="clothing", tags={'mall_shop'})
food = Block(label="food", tags={'mall_shop'})
```

**Push Pattern (Affordances)**
Blocks offer themselves to compatible menus:

```python
parking = Block(label="parking")
parking.offer_as_affordance(
    target_criteria={'has_tags': {'mall_lobby'}}
)

# Parking appears even though menu didn't ask for it
```

**Bidirectional (Both)**
Pull and push work together - menu gets both shops it asked for AND parking that volunteered.

### Scope Control

```python
# Only find blocks in same scene
menu = MenuBlock(
    selection_criteria={...},
    within_scene=True,  # Default
)

# Search entire graph
menu = MenuBlock(
    selection_criteria={...},
    within_scene=False,
)
```

### Action Labels

MenuBlock checks block metadata in order:
1. `locals['action_text']` - Explicit menu text
2. `locals['menu_text']` - Alternative menu text
3. `block.label` - Fallback to block's label

```python
shop = Block(
    label="clothing_store_id",
    locals={'action_text': "Shop for clothes"},  # This appears in menu
)
```

### Scene Navigation

When MenuBlock links to a Scene, it automatically creates Actions to `scene.source` (the canonical entry point), not to the Scene node itself.

### Implementation Notes

- Creates dependencies during PLANNING phase
- Materializes Actions during UPDATE phase
- Clears stale dynamic actions before reprovisioning
- Supports both pull (dependency) and push (affordance) patterns
- Inherits all Block rendering/journaling behavior
