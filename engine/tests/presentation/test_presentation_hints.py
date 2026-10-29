from tangl.presentation.hints import PresentationHints

### TestPresentationHints:
def test_presentation_hints():
    hints = PresentationHints(
        style_name="custom-style",
        style_tags=["primary", "highlight"],
        style_dict={"color": "blue", "font-weight": "bold"},
        icon="star"
    )
    assert hints.style_name == "custom-style"
    assert "primary" in hints.style_tags
    assert hints.style_dict["color"] == "blue"
    assert hints.icon == "star"

def test_presentation_hints_defaults():
    hints = PresentationHints()
    assert hints.style_tags == []
    assert hints.style_dict == {}
    assert hints.icon is None
    assert hints.icon_media is None
    assert hints.short_label is None
    assert hints.placement is None
    assert not hints.icon_only


def test_coarse_placement_is_typed_and_json_portable():
    import pytest
    from pydantic import ValidationError

    hints = PresentationHints(
        placement="middle", icon_only=True, icon="lamp", icon_media="pass.svg", short_label="HP",
    )
    assert PresentationHints.model_validate_json(hints.model_dump_json()) == hints
    with pytest.raises(ValidationError):
        PresentationHints(placement="top-left")
    with pytest.raises(ValidationError):
        PresentationHints(icon_media={"url": "https://example.test/icon.svg"})
    with pytest.raises(ValidationError):
        PresentationHints(short_label=["HP"])
