import uuid
from uuid import UUID

import pytest

from tangl.core.fragment import ContentFragment, ControlFragment


#### Base Fragment

def test_content_fragment_creation():
    # Test basic fragment creation
    fragment = ContentFragment(
        type="test",
        content="Test content"
    )
    assert fragment.fragment_type == "test"
    assert fragment.content == "Test content"
    assert fragment.uid is not None
    assert isinstance(fragment.uid, UUID)

def test_fragment_serialization():
    # Test that fragments serialize correctly
    fragment = ContentFragment(
        type="test",
        label="test_label",
        content="Test content",
        format="plain"
    )
    data = fragment.model_dump()
    assert data["fragment_type"] == "test"
    assert data["label"] == "test_label"
    assert data["content"] == "Test content"
    assert data["content_format"] == "plain"
    assert "uid" in data

def test_update_fragment():
    # Test update fragment creation and validation
    original_id = uuid.uuid4()
    update = ControlFragment(
        type="update",
        content="Updated content",
        ref_id=original_id
    )
    assert update.fragment_type == "update"
    assert update.reference_id == original_id
    assert update.reference_type == "content"


#### Activatable

@pytest.mark.xfail(raises=AttributeError, reason="belongs on story choice fragment")
def test_activatable_fragment():
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

