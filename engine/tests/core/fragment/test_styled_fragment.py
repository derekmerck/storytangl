from tangl.core.fragment import PresentationHints, StyledFragment

def test_text_fragment_creation():
    # Test text fragment with markdown
    fragment = StyledFragment(
        # type="content",
        content="# Test Heading\nThis is a test narrative.",
        format="markdown",
        hints=PresentationHints(
            style_name="story-text",
            style_tags=["important", "centered"],
            style_dict={"color": "red"}
        )
    )
    assert fragment.fragment_type == "content"
    assert fragment.content_format == "markdown"
    assert fragment.presentation_hints.style_tags == ["important", "centered"]
