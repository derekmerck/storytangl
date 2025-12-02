# The Crossroads Inn - Reference World

A comprehensive reference implementation demonstrating StoryTangl's core features.

## Overview

**The Crossroads Inn** serves as a complete example of a StoryTangl world bundle.
Follow a traveler who meets a mysterious guide and embarks on a journey.

## Features Demonstrated

- ✅ Multiple scenes with transitions
- ✅ Branching narrative paths  
- ✅ Character interactions
- ✅ State management
- ✅ Media integration (SVG images)
- ✅ Convention-based bundle format

## Bundle Structure

```
reference/
├── world.yaml          # Manifest
├── script.yaml         # Story script
├── README.md           # This file
└── media/
    └── images/
        ├── tavern.svg      # Tavern scene
        ├── forest.svg      # Forest path
        └── companion.svg   # Aria portrait
```

## Quick Start

### Python API

```python
from tangl.service.world_registry import WorldRegistry

# Discover and load
registry = WorldRegistry()
world = registry.get_world("reference")

# Create story instance
story = world.create_story("my_playthrough")

# Get starting block
start = story.get(story.initial_cursor_id)
print(start.content)
```

### CLI

```bash
# List worlds
tangl world list

# Play interactively
tangl play reference
```

## Story Structure

### Prologue: The Crossroads Inn
- Arrive at the tavern
- Meet Aria, the guide
- Learn about the Northern Pass

### Chapter 1: The Journey
- Trek through the forest
- Face a pivotal choice

### Epilogue: The Fortress
- Reach your destination
- [To be continued...]

## State Variables

- `companion_trust` - Aria's trust level
- `has_map` - Whether you obtained the map

## Extending

See the [main worlds README](../README.md) for details on:
- Adding new scenes
- Including media
- Custom domain classes
- Best practices

## License

MIT - Free to use as a template.

## Credits

Created by the StoryTangl team as a reference implementation.
