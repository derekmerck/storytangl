import pytest

pytest.skip(allow_module_level=True)

from tangl.journal.fragment import BaseFragment, GroupFragment

##### Grouped Fragments

TextFragment = MediaFragment = BaseFragment

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