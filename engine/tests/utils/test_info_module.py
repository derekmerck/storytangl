"""Tests for ``tangl.info`` metadata."""

from tangl import info


def test_info_metadata_consistency() -> None:
    """Ensure the published metadata remains consistent for clients."""
    assert info.__name__ == "tangl"
    assert info.__title__ == "StoryTangl"
    assert info.__desc__
    assert info.__url__.startswith("https://")
