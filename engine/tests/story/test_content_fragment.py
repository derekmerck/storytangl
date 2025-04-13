import pytest
import uuid
from uuid import UUID
from datetime import datetime
from typing import Any, Optional, Literal
from pydantic import BaseModel, Field

from tangl.story.journal.content_fragment_models import ContentFragment, UpdateFragment, TextFragment, KvFragment, GroupFragment, MediaFragment, MediaPresentationHints, PresentationHints


class TestContentFragment:
    def test_content_fragment_creation(self):
        # Test basic fragment creation
        fragment = ContentFragment(
            type="test",
            content="Test content"
        )
        assert fragment.fragment_type == "test"
        assert fragment.content == "Test content"
        assert fragment.uid is not None
        assert isinstance(fragment.uid, UUID)

    def test_fragment_serialization(self):
        # Test that fragments serialize correctly
        fragment = ContentFragment(
            type="test",
            label="test_label",
            content="Test content",
            format="plain"
        )
        data = fragment.model_dump()
        assert data["type"] == "test"
        assert data["label"] == "test_label"
        assert data["content"] == "Test content"
        assert data["format"] == "plain"
        assert "fragment_id" in data

    def test_update_fragment(self):
        # Test update fragment creation and validation
        original_id = uuid.uuid4()
        update = UpdateFragment(
            type="update",
            content="Updated content",
            ref_id=original_id
        )
        assert update.fragment_type == "update"
        assert update.reference_id == original_id
        assert update.reference_type == "content"


class TestTextFragment:
    def test_text_fragment_creation(self):
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

    def test_text_fragment_defaults(self):
        # Test default values
        fragment = TextFragment(
            type="text",
            content="Simple text"
        )
        assert fragment.content_format == "plain"
        assert fragment.presentation_hints is None


class TestKvFragment:
    def test_kv_fragment_creation(self):
        # Test KV fragment with different value types
        fragment = KvFragment(
            type="kv",
            key="score",
            value=100
        )
        assert fragment.fragment_type == "kv"
        assert fragment.label == "score"
        assert fragment.content == 100

    def test_kv_fragment_with_complex_value(self):
        # Test with complex value
        complex_value = {"points": 100, "level": 5, "achievements": ["gold", "silver"]}
        fragment = KvFragment(
            type="kv",
            key="player_stats",
            value=complex_value
        )
        assert fragment.content == complex_value


class TestMediaFragment:
    def test_media_fragment_with_url(self):
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

    def test_media_fragment_with_binary_data(self):
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


class TestPresentationHints:
    def test_presentation_hints(self):
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

    def test_presentation_hints_defaults(self):
        hints = PresentationHints()
        assert hints.style_tags == []
        assert hints.style_dict == {}
        assert hints.icon is None


class TestFragmentActivation:
    def test_activatable_fragment(self):
        # Test fragment with activation capability
        fragment = ContentFragment(
            type="choice",
            content="Choose this option",
            activatable=True,
            activation_payload={"action": "select_option", "option_id": 5}
        )
        assert fragment.activatable is True
        assert fragment.active is True
        assert fragment.activation_payload["option_id"] == 5


class TestGroupFragments:
    def test_group_creation_and_membership(self):
        # Create a group fragment representing a dialog exchange
        group = GroupFragment(
            type="group",
            group_type="dialog_exchange",
            group_roles=[
                {"role": "speaker", "type": "text"},
                {"role": "avatar", "type": "image", "optional": True},
                {"role": "dialog", "type": "text"}
            ]
        )

        # Create member fragments
        speaker = TextFragment(
            type="text",
            content="Commander Shepard:",
            group_id=group.uid,
            group_role="speaker"
        )

        avatar = MediaFragment(
            type="image",
            content="https://example.com/shepard.jpg",
            format="url",
            group_id=group.uid,
            group_role="avatar"
        )

        dialog = TextFragment(
            type="text",
            content="I'm Commander Shepard, and this is my favorite store on the Citadel.",
            format="plain",
            group_id=group.uid,
            group_role="dialog"
        )

        # Assertions
        assert group.fragment_type == "group"
        assert speaker.group_id == group.uid
        assert avatar.group_id == group.uid
        assert dialog.group_id == group.uid

        # Simulate a client that recognizes grouping
        def collect_group_members(group_id, fragments):
            return [f for f in fragments if f.group_id == group_id]

        all_fragments = [group, speaker, avatar, dialog]
        group_members = collect_group_members(group.uid, all_fragments)
        assert len(group_members) == 3

        # Ensure the grouping is just a logical construct
        serialized_response = [f.model_dump() for f in all_fragments]
        assert len(serialized_response) == 4  # Still a flat list