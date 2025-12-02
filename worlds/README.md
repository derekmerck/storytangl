# StoryTangl Worlds

World bundles for the StoryTangl narrative engine.

## Available Worlds

### reference/
**The Crossroads Inn** - Complete reference implementation.

See [reference/README.md](reference/README.md) for details.

## Creating a New World

### Quick Start

```bash
# Copy reference as template
cp -r worlds/reference worlds/my_world

# Update manifest
vim worlds/my_world/world.yaml
# Change: label: my_world

# Edit story
vim worlds/my_world/script.yaml
```

### From Scratch

```bash
mkdir -p worlds/my_world/media/images

cat > worlds/my_world/world.yaml <<EOF
label: my_world
metadata:
  title: "My Story"
  author: "Your Name"
EOF

cat > worlds/my_world/script.yaml <<EOF
label: my_world
scenes:
  intro:
    blocks:
      start:
        content: "Your story begins..."
EOF
```

## Discovery

Worlds are automatically discovered if:
1. Directory name matches `label` in world.yaml
2. Located in configured world paths

Default: `./worlds`

Configure in `settings.toml`:

```toml
[service.paths]
worlds = ["./worlds"]
```

## Loading Worlds

### Python

```python
from tangl.service.world_registry import WorldRegistry

registry = WorldRegistry()
world = registry.get_world("reference")
```

### CLI

```bash
tangl world list
tangl play reference
```

## Bundle Format

### Manifest (world.yaml)

```yaml
label: my_world          # Must match directory name
scripts: script.yaml     # Optional (convention-based)
media_dir: media         # Optional (defaults to "media")
metadata:
  title: "My Story"
  author: "Your Name"
  version: "1.0.0"
```

### Script (script.yaml)

```yaml
label: my_world
metadata:
  title: "My Story"

scenes:
  intro:
    blocks:
      start:
        content: "Narrative text"
        actions:
          - text: "Choice text"
            successor: next_block
```

## Best Practices

1. Directory name = manifest label
2. Include README.md
3. Use conventions (script.yaml, media/)
4. Test with WorldRegistry
5. Version in metadata

## Troubleshooting

### World not discovered?

```python
from tangl.service.world_registry import WorldRegistry
from pathlib import Path

registry = WorldRegistry([Path("./worlds")])
print(registry.list_worlds())
```

### Label mismatch?

```bash
# Check consistency
cat worlds/my_world/world.yaml | grep label
```

## Contributing

New reference worlds welcome! Submit via pull request.
