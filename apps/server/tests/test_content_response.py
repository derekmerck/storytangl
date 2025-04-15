import pytest
from datetime import datetime, timedelta
from uuid import UUID
from pydantic import ValidationError
import pytest

pytest.skip(allow_module_level=True)

import tangl.info  # Mock this if needed for tests
from tangl.story.journal.content_fragment_models import ContentFragment, TextFragment, KvFragment, MediaFragment, GroupFragment, UserEventFragment
from tangl.rest.content_response import ContentResponse


class TestContentResponse:
    def test_basic_content_response(self):
        # Test creating a response with a list of fragments
        fragments = [
            TextFragment(type="text", content="Hello world"),
            KvFragment(type="kv", key="score", value=100)
        ]

        response = ContentResponse(data=fragments)

        assert response.schema_version == ".".join(tangl.info.__version__.split(".")[0:1])
        assert isinstance(response.uid, UUID)
        assert isinstance(response.timestamp, datetime)
        assert len(response.data) == 2
        assert response.data[0].content == "Hello world"
        assert response.data[1].content == 100

    def test_dict_to_kv_conversion(self):
        # Test automatic conversion of dict to KvFragments
        response = ContentResponse(data={
            "name": "John Doe",
            "level": 5,
            "inventory": ["sword", "shield", "potion"]
        })

        assert len(response.data) == 3
        assert all(isinstance(f, KvFragment) for f in response.data)

        # Verify the conversion worked correctly
        name_fragment = next(f for f in response.data if f.label == "name")
        assert name_fragment.content == "John Doe"

        inventory_fragment = next(f for f in response.data if f.label == "inventory")
        assert inventory_fragment.content == ["sword", "shield", "potion"]

    def test_serialization(self):
        # Test that response serializes correctly
        fragments = [
            TextFragment(type="text", content="Test content")
        ]

        response = ContentResponse(data=fragments)
        data = response.model_dump()

        assert "schema_version" in data
        assert "response_id" in data
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)  # Serialized as ISO format
        assert isinstance(data["data"], list)
        assert data["data"][0]["type"] == "text"

    def test_mixed_fragment_types(self):
        # Test a response with various fragment types
        fragments = [
            TextFragment(type="text", content="Title", format="markdown"),
            MediaFragment(type="image", content="https://example.com/image.jpg", format="url"),
            KvFragment(type="kv", key="status", value="active"),
            # Add your GroupFragment if implemented
            GroupFragment(
                type="group",
                group_type="dialog",
                expected_children=[
                    {"role": "speaker", "type": "text"},
                    {"role": "text", "type": "text"}
                ]
            )
        ]

        response = ContentResponse(data=fragments)

        # Check that all fragments are preserved with correct types
        assert isinstance(response.data[0], TextFragment)
        assert isinstance(response.data[1], MediaFragment)
        assert isinstance(response.data[2], KvFragment)
        assert isinstance(response.data[3], GroupFragment)

        # Check fragment-specific properties
        assert response.data[0].content_format == "markdown"
        assert response.data[1].content_format == "url"
        assert response.data[2].label == "status"
        assert response.data[3].group_type == "dialog"

    def test_empty_response(self):
        # Test with empty data list
        with pytest.raises(ValidationError):
            ContentResponse(data=[])

    def test_fragment_sequence_ordering(self):
        # Test fragments with sequence numbers
        fragments = [
            TextFragment(type="text", content="Third", sequence=3),
            TextFragment(type="text", content="First", sequence=1),
            TextFragment(type="text", content="Second", sequence=2)
        ]

        response = ContentResponse(data=fragments)

        # If you implement the get_ordered_fragments method
        ordered = response.get_ordered_fragments()
        assert ordered[0].content == "First"
        assert ordered[1].content == "Second"
        assert ordered[2].content == "Third"