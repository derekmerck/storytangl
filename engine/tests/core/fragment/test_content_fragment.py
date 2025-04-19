import uuid
from uuid import UUID

from tangl.core.fragment import ContentFragment, UpdateFragment, KvFragment, GroupFragment, PresentationHints

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
    assert data["type"] == "test"
    assert data["label"] == "test_label"
    assert data["content"] == "Test content"
    assert data["format"] == "plain"
    assert "uid" in data

def test_update_fragment():
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


#### TestKvFragment

def test_kv_fragment_creation():
    # Test KV fragment with different value types
    fragment = KvFragment(
        type="kv",
        key="score",
        value=100
    )
    assert fragment.fragment_type == "kv"
    assert fragment.label == "score"
    assert fragment.content == 100

def test_kv_fragment_with_complex_value():
    # Test with complex value
    complex_value = {"points": 100, "level": 5, "achievements": ["gold", "silver"]}
    fragment = KvFragment(
        type="kv",
        key="player_stats",
        value=complex_value
    )
    assert fragment.content == complex_value


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


#### Activatable

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


##### Grouped Fragments

TextFragment = MediaFragment = ContentFragment

def test_group_creation_and_membership():
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