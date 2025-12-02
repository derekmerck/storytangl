#!/usr/bin/env python3
"""
setup_reference_world.py

Automated setup for StoryTangl reference world.
Can be run from repo root OR from scripts/ directory.
"""

import sys
from pathlib import Path


def find_repo_root() -> Path:
    """Find repo root by looking for pyproject.toml and engine/ dir."""
    current = Path.cwd()
    
    # Check current directory
    if (current / "pyproject.toml").exists() and (current / "engine").is_dir():
        return current
    
    # Check parent directory (if we're in scripts/)
    parent = current.parent
    if (parent / "pyproject.toml").exists() and (parent / "engine").is_dir():
        return parent
    
    print("❌ ERROR: Cannot find repo root!")
    print("   Please run from repo root or scripts/ directory")
    sys.exit(1)


def create_world_yaml(path: Path) -> None:
    """Create world.yaml manifest."""
    content = """label: reference

metadata:
  title: "The Crossroads Inn"
  author: "StoryTangl Team"
  version: "1.0.0"
  description: >
    A reference world demonstrating StoryTangl features including
    multiple scenes, character interactions, state management,
    and media integration.
  
  tags:
    - reference
    - tutorial
    - complete-example
  
  ir_schema: "3.7"
  license: "MIT"

# Convention-based discovery (uncomment to be explicit)
# scripts: script.yaml
# media_dir: media
"""
    path.write_text(content, encoding="utf-8")


def create_script_yaml(path: Path) -> None:
    """Create script.yaml story."""
    content = """label: crossroads_inn

metadata:
  title: "The Crossroads Inn"
  author: "StoryTangl Team"

scenes:
  prologue:
    label: prologue
    
    templates:
      aria:
        obj_cls: "tangl.story.concepts.actor.actor.Actor"
        name: "Aria"
        tags: ["companion", "main"]
    
    blocks:
      start:
        label: start
        content: |
          The Crossroads Inn sits at the junction of three ancient roads.
          Rain patters against the windows as you push open the heavy oak door.
          
          The common room is warm and inviting, lit by a crackling fireplace.
          A few patrons sit scattered at wooden tables.
        
        media:
          - name: tavern.svg
            media_role: narrative_im
        
        locals:
          companion_trust: 0
          has_map: false
        
        actions:
          - text: "Approach the fireplace"
            successor: meet_aria
          - text: "Talk to the innkeeper"
            successor: innkeeper
      
      meet_aria:
        label: meet_aria
        content: |
          You approach the fireplace. The cloaked figure looks up,
          revealing sharp eyes and a weathered face.
          
          "Aria," she introduces herself simply. "Looking for work,
          or just passing through?"
        
        media:
          - name: companion.svg
            media_role: character_portrait
        
        actions:
          - text: "I'm looking for the Northern Pass"
            successor: request_help
          
          - text: "Just warming up before moving on"
            successor: start
      
      request_help:
        label: request_help
        content: |
          Aria's expression softens slightly. "The Northern Pass?
          Dangerous this time of year." She pauses. "But I know the way.
          For the right price, I could guide you."
        
        actions:
          - text: "Offer to split any treasure found"
            successor: chapter1.trail_start
          
          - text: "Politely decline"
            successor: start
      
      innkeeper:
        label: innkeeper
        content: |
          The innkeeper, a portly man with a bushy mustache,
          greets you warmly. "Welcome, traveler! What'll it be?"
        
        actions:
          - text: "Ask about rumors"
            successor: rumors
          - text: "Return to the common room"
            successor: start
      
      rumors:
        label: rumors
        content: |
          "Well," the innkeeper leans in conspiratorially, "they say
          the old fortress in the Northern Pass holds treasure beyond
          measure. But the way is treacherous, and strange things
          have been seen in those mountains..."
        
        actions:
          - text: "Thank him and return"
            successor: start
  
  chapter1:
    label: chapter1
    
    blocks:
      trail_start:
        label: trail_start
        content: |
          You and Aria set out at dawn. The forest path is narrow
          and overgrown, but she navigates it with practiced ease.
        
        media:
          - name: forest.svg
            media_role: narrative_im
        
        actions:
          - text: "Continue deeper into the forest"
            successor: forest_encounter
      
      forest_encounter:
        label: forest_encounter
        content: |
          A fork in the path appears ahead. Aria pauses, studying
          both options carefully.
        
        actions:
          - text: "Take the left path (faster but riskier)"
            successor: epilogue.left_path
          - text: "Take the right path (safer but longer)"
            successor: epilogue.right_path
  
  epilogue:
    label: epilogue
    
    blocks:
      left_path:
        label: left_path
        content: |
          The left path proves treacherous. After a harrowing climb,
          you reach the Pass, but Aria is impressed by your courage.
        
        actions:
          - text: "Enter the fortress"
            successor: end
      
      right_path:
        label: right_path
        content: |
          The right path is longer but safer. You arrive at the Pass
          as the sun sets, exhausted but unharmed.
        
        actions:
          - text: "Make camp"
            successor: end
      
      end:
        label: end
        content: |
          The ancient fortress looms before you, silhouetted against
          the evening sky. Your adventure is just beginning...
          
          [To be continued]
"""
    path.write_text(content, encoding="utf-8")


def create_tavern_svg(path: Path) -> None:
    """Create tavern.svg media asset."""
    content = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
  <rect x="50" y="100" width="300" height="150" fill="#8B4513" stroke="#654321" stroke-width="3"/>
  <polygon points="50,100 200,50 350,100" fill="#A0522D"/>
  <rect x="150" y="180" width="100" height="70" fill="#3E2723"/>
  <circle cx="200" cy="215" r="3" fill="#FFD700"/>
  <rect x="100" y="130" width="50" height="50" fill="#87CEEB" stroke="#654321" stroke-width="2"/>
  <rect x="250" y="130" width="50" height="50" fill="#87CEEB" stroke="#654321" stroke-width="2"/>
  <text x="200" y="280" text-anchor="middle" font-size="20" fill="#654321">The Crossroads Inn</text>
</svg>
"""
    path.write_text(content, encoding="utf-8")


def create_forest_svg(path: Path) -> None:
    """Create forest.svg media asset."""
    content = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
  <rect width="400" height="300" fill="#87CEEB"/>
  <ellipse cx="100" cy="250" rx="80" ry="50" fill="#228B22"/>
  <rect x="90" y="200" width="20" height="100" fill="#654321"/>
  <ellipse cx="250" cy="220" rx="100" ry="80" fill="#228B22"/>
  <rect x="240" y="150" width="20" height="150" fill="#654321"/>
  <ellipse cx="350" cy="260" rx="60" ry="40" fill="#228B22"/>
  <rect x="345" y="220" width="10" height="80" fill="#654321"/>
  <path d="M 50 280 Q 200 250 350 280" fill="none" stroke="#8B7355" stroke-width="30"/>
  <text x="200" y="290" text-anchor="middle" font-size="16" fill="#333">The Forest Path</text>
</svg>
"""
    path.write_text(content, encoding="utf-8")


def create_companion_svg(path: Path) -> None:
    """Create companion.svg media asset."""
    content = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="300" viewBox="0 0 200 300">
  <ellipse cx="100" cy="80" rx="40" ry="50" fill="#4A4A4A"/>
  <rect x="70" y="120" width="60" height="120" fill="#4A4A4A" rx="10"/>
  <rect x="40" y="140" width="30" height="80" fill="#4A4A4A"/>
  <rect x="130" y="140" width="30" height="80" fill="#4A4A4A"/>
  <rect x="70" y="235" width="25" height="60" fill="#4A4A4A"/>
  <rect x="105" y="235" width="25" height="60" fill="#4A4A4A"/>
  <circle cx="85" cy="70" r="5" fill="#FFE4B5"/>
  <circle cx="115" cy="70" r="5" fill="#FFE4B5"/>
  <text x="100" y="295" text-anchor="middle" font-size="14" fill="#333">Aria</text>
</svg>
"""
    path.write_text(content, encoding="utf-8")

def create_reference_gitattributes(path: Path) -> None:
    """Create .gitattributes override for reference world."""
    content = """# Reference world media override
# Keep demo SVGs as regular text (not LFS)
# This overrides the root **/media/** LFS rule for SVG files
media/** -filter -diff -merge text
"""
    path.write_text(content, encoding="utf-8")

def create_world_readme(path: Path) -> None:
    """Create reference world README."""
    content = """# The Crossroads Inn - Reference World

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
"""
    path.write_text(content, encoding="utf-8")


def create_worlds_readme(path: Path) -> None:
    """Create worlds/ README."""
    content = """# StoryTangl Worlds

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
"""
    path.write_text(content, encoding="utf-8")


def create_validation_script(path: Path) -> None:
    """Create worlds/validate.py script."""
    content = '''#!/usr/bin/env python3
"""Validate all worlds in directory."""

from pathlib import Path
import sys

# Add engine to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "engine" / "src"))

try:
    from tangl.service.world_registry import WorldRegistry
    from tangl.loaders import WorldBundle
except ImportError as e:
    print(f"❌ Cannot import tangl: {e}")
    print(f"   Repo root: {repo_root}")
    print(f"   Engine path: {repo_root / 'engine' / 'src'}")
    sys.exit(1)

def validate_worlds(worlds_dir: Path):
    print(f"Validating worlds in {worlds_dir}")
    print("=" * 60)
    
    for world_dir in worlds_dir.iterdir():
        if not world_dir.is_dir() or world_dir.name.startswith('.'):
            continue
        
        print(f"\\n{world_dir.name}:")
        
        manifest_path = world_dir / "world.yaml"
        if not manifest_path.exists():
            print("  ❌ No world.yaml found")
            continue
        
        try:
            bundle = WorldBundle.load(world_dir)
            print(f"  ✅ Bundle loaded")
            print(f"     Label: {bundle.manifest.label}")
            print(f"     Title: {bundle.manifest.metadata.get('title', 'N/A')}")
            
            if bundle.manifest.label != world_dir.name:
                print(f"  ⚠️  Label mismatch: {bundle.manifest.label} != {world_dir.name}")
            
            try:
                scripts = bundle.script_paths
                print(f"  ✅ Scripts: {len(scripts)} file(s)")
                for script in scripts:
                    print(f"     - {script.relative_to(world_dir)}")
            except Exception as e:
                print(f"  ❌ Script error: {e}")
            
            if bundle.media_dir.exists():
                media_files = [f for f in bundle.media_dir.rglob("*") if f.is_file()]
                print(f"  ✅ Media: {len(media_files)} file(s)")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\\n" + "=" * 60)
    print("Discovery test:\\n")
    
    try:
        registry = WorldRegistry([worlds_dir])
        discovered = registry.list_worlds()
        print(f"✅ Discovered {len(discovered)} world(s):")
        for world_info in discovered:
            print(f"  - {world_info['label']}: {world_info['metadata'].get('title', 'N/A')}")
    except Exception as e:
        print(f"❌ Discovery failed: {e}")

if __name__ == "__main__":
    worlds_dir = Path(__file__).parent
    validate_worlds(worlds_dir)
'''
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)  # Make executable


def main():
    """Main setup routine."""
    print("=" * 60)
    print("StoryTangl Reference World Setup")
    print("=" * 60)
    print()
    
    # Find repo root
    repo_root = find_repo_root()
    worlds_dir = repo_root / "worlds"
    ref_dir = worlds_dir / "reference"
    
    print(f"Repo root: {repo_root}")
    print(f"Target:    {ref_dir}")
    print()
    
    # Step 1: Create directories
    print("Step 1: Creating directory structure...")
    (ref_dir / "media" / "images").mkdir(parents=True, exist_ok=True)
    (ref_dir / "media" / "audio").mkdir(parents=True, exist_ok=True)
    print("✓ Directories created")
    print()
    
    # Step 2: Create world.yaml
    print("Step 2: Creating world.yaml...")
    create_world_yaml(ref_dir / "world.yaml")
    print("✓ world.yaml created")
    print()
    
    # Step 3: Create script.yaml
    print("Step 3: Creating script.yaml...")
    create_script_yaml(ref_dir / "script.yaml")
    print("✓ script.yaml created")
    print()
    
    # Step 4: Create media files
    print("Step 4: Creating media assets...")
    create_tavern_svg(ref_dir / "media" / "images" / "tavern.svg")
    create_forest_svg(ref_dir / "media" / "images" / "forest.svg")
    create_companion_svg(ref_dir / "media" / "images" / "companion.svg")
    print("✓ Media assets created (3 SVG files)")
    print()

    # Step 5: Create .gitattributes override
    print("Step 5: Creating .gitattributes override...")
    create_reference_gitattributes(ref_dir / ".gitattributes")
    print("✓ .gitattributes created (media stays as text)")
    print()
    
    # Step 6: Create world README
    print("Step 6: Creating world README...")
    create_world_readme(ref_dir / "README.md")
    print("✓ README.md created")
    print()
    
    # Step 7: Create worlds README
    print("Step 7: Creating worlds README...")
    create_worlds_readme(worlds_dir / "README.md")
    print("✓ Worlds README created")
    print()
    
    # Step 8: Create validation script
    print("Step 8: Creating validation script...")
    create_validation_script(worlds_dir / "validate.py")
    print("✓ Validation script created")
    print()
    
    # Step 9: Run validation
    print("Step 9: Running validation...")
    sys.path.insert(0, str(repo_root / "engine" / "src"))
    
    try:
        from tangl.service.world_registry import WorldRegistry
        from tangl.loaders import WorldBundle
        
        # Quick validation
        bundle = WorldBundle.load(ref_dir)
        print(f"  ✅ Bundle loads: {bundle.manifest.label}")
        
        registry = WorldRegistry([worlds_dir])
        worlds = registry.list_worlds()
        print(f"  ✅ Discovered {len(worlds)} world(s)")
        
    except Exception as e:
        print(f"  ⚠️  Validation incomplete: {e}")
        print("     (Run validate.py manually for full check)")
    
    print()
    print("=" * 60)
    print("✓ Reference world setup complete!")
    print("=" * 60)
    print()
    print(f"Location: {ref_dir}")
    print()
    print("Next steps:")
    print(f"  1. Review: cat {ref_dir / 'README.md'}")
    print(f"  2. Test: cd {worlds_dir} && python validate.py")
    print("  3. Play: cd apps/cli && python -m tangl.cli play reference")
    print()


if __name__ == "__main__":
    main()
