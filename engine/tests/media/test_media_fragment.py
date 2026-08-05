# pytest.skip("deprecated", allow_module_level=True)

from base64 import b64encode

import pytest

from tangl.core import Graph
from tangl.journal.media import MediaFragment, StagingHints
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaRITStatus, MediaResourceInventoryTag as MediaRIT
from tangl.service.media import media_fragment_to_payload
from tangl.vm import Ledger

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


def test_media_fragment_rit_round_trip_requires_an_owning_graph():
    """A standalone persisted fragment cannot fabricate a graph-owned RIT."""

    rit = MediaRIT(data="<svg/>", data_type=MediaDataType.VECTOR)
    fragment = MediaFragment(
        content=rit,
        content_type=MediaDataType.VECTOR,
        content_format="rit",
    )

    payload = fragment.unstructure()

    assert payload["rit_id"] == rit.uid
    assert "content" not in payload
    with pytest.raises(ValueError, match="requires an owning graph"):
        MediaFragment.structure(payload)


def test_ledger_round_trip_rebinds_media_fragment_to_the_restored_rit():
    """Persisted journal media observes the restored graph resource lifecycle."""

    graph = Graph()
    start = graph.add_node(label="start")
    rit = MediaRIT(data="<svg/>", data_type=MediaDataType.VECTOR)
    graph.add(rit)
    ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
    fragment = MediaFragment(
        content=rit,
        content_type=MediaDataType.VECTOR,
        content_format="rit",
    )
    ledger.output_stream.append(fragment)

    restored = Ledger.structure(ledger.unstructure())
    restored_fragment = next(
        item for item in restored.output_stream.values() if isinstance(item, MediaFragment)
    )
    restored_rit = restored.graph.get(rit.uid)

    assert restored_fragment.content is restored_rit
    restored_rit.status = MediaRITStatus.PENDING
    assert media_fragment_to_payload(restored_fragment) is None


@pytest.mark.parametrize(
    ("content_format", "content", "expected_key"),
    [
        ("url", "https://example.com/card.svg", "url"),
        ("data", b"card-data", "data"),
        ("json", {"url": "https://example.com/card.svg"}, "url"),
        ("xml", "<svg/>", "content"),
    ],
)
def test_direct_media_payloads_keep_fragment_uid(
    content_format: str,
    content: str | bytes | dict[str, str],
    expected_key: str,
) -> None:
    """Every direct media transport shape preserves the fragment relationship ID."""

    fragment = MediaFragment(
        content=content,
        content_type=MediaDataType.VECTOR,
        content_format=content_format,
    )

    payload = media_fragment_to_payload(fragment)

    assert payload is not None
    assert payload["uid"] == str(fragment.uid)
    assert expected_key in payload
