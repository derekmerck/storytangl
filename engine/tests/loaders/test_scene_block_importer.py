"""Tests for legacy scene/block importers.

Organized by functionality:
- Scene/block conversion into addressable templates.
"""

from __future__ import annotations

from tangl.loaders.legacy.scene_block_importer import SceneBlockImporter


# ============================================================================
# Scene/block conversion
# ============================================================================


class TestSceneBlockImporter:
    """Tests for converting legacy scene/block structures."""

    def test_convert_scenes_to_templates_builds_hierarchy(self) -> None:
        """Convert scene blocks into templates with hierarchical paths."""

        importer = SceneBlockImporter()
        templates = importer.convert_scenes_to_templates(
            {
                "inn": {
                    "label": "inn",
                    "blocks": {
                        "entrance": {"content": "Welcome"},
                        "hall": {"content": "The common hall"},
                    },
                }
            }
        )

        assert len(templates) == 1

        scene = templates[0]
        assert scene.label == "inn"
        assert scene.declares_instance is True

        entrance = scene.blocks["entrance"]
        assert entrance.label == "entrance"
        assert entrance.declares_instance is True
        assert entrance.path == "inn.entrance"
