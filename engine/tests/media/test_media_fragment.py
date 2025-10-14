# pytest.skip("deprecated", allow_module_level=True)

from tangl.journal.media import MediaFragment, StagingHints

def test_media_fragment_with_url():
    # Test media fragment with URL
    fragment = MediaFragment(
        fragment_type="image",
        content="https://example.com/image.jpg",
        content_type="image",
        content_format="url",
        staging_hints=StagingHints(
            media_shape="landscape",
            media_size="medium",
            media_transition="fade_in"
        )
    )
    assert fragment.fragment_type == "image"
    assert fragment.content == "https://example.com/image.jpg"
    assert fragment.content_format == "url"
    assert fragment.staging_hints.media_shape == "landscape"
    assert fragment.staging_hints.media_size == "medium"

def test_media_fragment_with_binary_data():
    # Test with binary data
    binary_data = b"test binary data"
    fragment = MediaFragment(
        type="fragment",
        content=binary_data,
        content_type="image",
        content_format="data",
    )
    # Check that binary data is properly handled
    serialized = fragment.model_dump()
    # Binary should be properly encoded
    assert serialized["content"] != binary_data

