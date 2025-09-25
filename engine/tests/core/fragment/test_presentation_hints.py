from tangl.core.fragment import PresentationHints

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

