#!/usr/bin/env python3
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
        
        print(f"\n{world_dir.name}:")
        
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
    
    print("\n" + "=" * 60)
    print("Discovery test:\n")
    
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
