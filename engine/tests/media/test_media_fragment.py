# pytest.skip("deprecated", allow_module_level=True)

from base64 import b64encode

from tangl.journal.media import MediaFragment, StagingHints
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT

def test_media_fragment_with_url():
    # Test media fragment with URL
    fragment = MediaFragment(
        content="https://example.com/image.jpg",
        content_type="image",
        content_format="url",
        staging_hints=StagingHints(
            media_shape="landscape",
            media_size="medium",
            media_transition="fade_in"
        )
    )
    assert fragment.fragment_type == "media"
    assert fragment.content_type.value == "image"
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
    assert serialized["content"] == b64encode(binary_data).decode("utf-8")


def test_media_fragment_round_trip_keeps_rit_content():
    """Journal persistence retains a dereferenceable generated-media RIT."""

    rit = MediaRIT(data="<svg/>", data_type=MediaDataType.VECTOR)
    fragment = MediaFragment(
        content=rit,
        content_type=MediaDataType.VECTOR,
        content_format="rit",
    )

    restored = MediaFragment.structure(fragment.unstructure())

    assert isinstance(restored.content, MediaRIT)
    assert restored.content.uid == rit.uid
