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
codec: near_native       # Optional (default: near_native)
scripts: script.yaml     # Optional (legacy single-story shorthand)
media_dir: media         # Optional (defaults to "media")
metadata:
  title: "My Story"
  author: "Your Name"
  version: "1.0.0"
```

### Multi-Story Manifest (anthology)

```yaml
label: my_anthology
codec: near_native
metadata:
  title: "My Anthology"
stories:
  book1:
    scripts:
      - content/book1.yaml
  book2:
    codec: near_native
    scripts:
      - content/book2_part1.yaml
      - content/book2_part2.yaml
```

### Twine / Twee 3 Manifest

```yaml
label: twine_reference
codec: twee3_1_0
metadata:
  author: "StoryTangl Team"
scripts: story.twee
```

### Codec contract (first pass)

StoryTangl now treats the runtime representation as canonical and delegates
on-disk translation to codecs.

- `decode`: on-disk source -> runtime-ready script data (+ provenance map)
- `encode`: runtime data -> on-disk source shape

Current status:
1. Built-in near-native YAML codec is included.
2. Built-in Twine / Twee 3 import is available as `twine`, `twee`, `twee3`,
   and `twee3_1_0`.
3. The Twine codec currently supports passage headers, `StoryTitle`,
   `StoryData`, plain prose, basic `[[...]]` link forms, simple `<<set>>`
   assignments, and link-only `<<if>>` / `<<elseif>>` / `<<else>>` gating with
   optional simple link setters.
4. Source mapping is file-level only (`__source_files__`) in MVP.
5. Per-node/per-span mapping is intentionally deferred.
6. Unknown codecs can still be bridged by custom script compilers that expose
   `load_from_path` (migration shortcut, not long-term architecture).

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
2. Prefer explicit `stories:` for multi-story bundles.
3. Keep codec choice explicit when you are not using near-native YAML.
4. Include README.md
5. Use conventions (script.yaml, media/)
6. Test with WorldRegistry
7. Version in metadata

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
