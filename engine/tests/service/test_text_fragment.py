from tangl.core.solver import PresentationHints
from tangl.story.journal import TextFragment

def test_text_fragment_creation():
    # Test text fragment with markdown
    fragment = TextFragment(
        type="narrative",
        content="# Test Heading\nThis is a test narrative.",
        format="markdown",
        hints=PresentationHints(
            style_name="story-text",
            style_tags=["important", "centered"],
            style_dict={"color": "red"}
        )
    )
    assert fragment.fragment_type == "narrative"
    assert fragment.content_format == "markdown"
    assert fragment.presentation_hints.style_tags == ["important", "centered"]

def test_text_fragment_defaults():
    # Test default values
    fragment = TextFragment(
        type="text",
        content="Simple text"
    )
    assert fragment.content_format == "plain"
    assert fragment.presentation_hints is None

