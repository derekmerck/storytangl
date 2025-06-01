import pytest

pytest.skip("deprecated", allow_module_level=True)

from tangl.media.media_fragment import MediaFragment, MediaPresentationHints

def test_media_fragment_with_url():
    # Test media fragment with URL
    fragment = MediaFragment(
        type="image",
        content="https://example.com/image.jpg",
        format="url",
        media_hints=MediaPresentationHints(
            media_shape="landscape",
            media_size="medium",
            media_transition="fade_in"
        )
    )
    assert fragment.fragment_type == "image"
    assert fragment.content == "https://example.com/image.jpg"
    assert fragment.content_format == "url"
    assert fragment.media_hints.media_shape == "landscape"

def test_media_fragment_with_binary_data():
    # Test with binary data
    binary_data = b"test binary data"
    fragment = MediaFragment(
        type="image",
        content=binary_data,
        format="data"
    )
    # Check that binary data is properly handled
    serialized = fragment.model_dump()
    # Binary should be properly encoded
    assert serialized["content"] != binary_data

