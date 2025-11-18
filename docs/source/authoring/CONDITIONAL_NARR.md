# Conditional Narratives in StoryTangl

## State Variables

Define global state in your script:

```yaml
globals:
  has_key: false
  player_health: 100
```

## Effects

Modify state when blocks are entered:

```yaml
effects:
  - "has_key = True"
  - "player_health -= 10"
```

## Conditions

Gate actions based on state:

```yaml
actions:
  - text: "Use the key"
    conditions:
      - "has_key"
  
  - text: "Break down the door"
    conditions:
      - "player_health > 50"
```

## Items and Flags

```yaml
items:
  sword:
    name: "Iron Sword"

effects:
  - "acquire_item('sword')"

conditions:
  - "has_item('sword')"
```