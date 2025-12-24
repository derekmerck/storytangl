from pathlib import Path
from tangl.service.world_registry import WorldRegistry
from tangl.ir.story_ir import BlockScript

def test_registry_has_blocks_for_export(media_mvp_path: Path):
    """Minimal check: can we export block templates?"""

    registry = WorldRegistry([media_mvp_path.parent])
    world = registry.get_world("media_mvp")

    # Must have blocks
    blocks = list(world.find_templates(is_instance=BlockScript))
    assert len(blocks) > 0

    # Must have serialization interface
    for block in blocks:
        dumped = block.model_dump(exclude_defaults=True)
        assert "label" in dumped
        assert "text" in dumped or "content" in dumped

    # Can infer scenes from scopes
    scene_labels = {b.parent.label for b in blocks if b.parent}
    assert len(scene_labels) > 0  # At least one scene

    print(f"✓ Registry has {len(blocks)} blocks across {len(scene_labels)} scenes")