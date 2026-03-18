from __future__ import annotations

from tangl.core import Registry
from tangl.journal.content import ContentFragment as LegacyContentFragment
from tangl.journal.fragments import (
    ChoiceFragment,
    ContentFragment,
    GroupFragment,
    MediaFragment,
    PresentationHints,
)
from tangl.journal.media import MediaFragment as LegacyMediaFragment
from tangl.journal.prose import ChoiceFragment as LegacyChoiceFragment
from tangl.story.fragments import ChoiceFragment as StoryChoiceFragment
from tangl.story.fragments import ContentFragment as StoryContentFragment
from tangl.story.fragments import MediaFragment as StoryMediaFragment


def test_canonical_fragment_import_surface_is_shared() -> None:
    assert LegacyContentFragment is ContentFragment
    assert LegacyChoiceFragment is ChoiceFragment
    assert LegacyMediaFragment is MediaFragment
    assert StoryContentFragment is ContentFragment
    assert StoryChoiceFragment is ChoiceFragment
    assert StoryMediaFragment is MediaFragment


def test_group_fragment_members_resolve_by_member_ids() -> None:
    registry: Registry[ContentFragment] = Registry(label="fragments")
    first = ContentFragment(content="first")
    second = ContentFragment(content="second")
    registry.add(first)
    registry.add(second)

    group = GroupFragment(
        member_ids=[first.uid, second.uid],
        hints=PresentationHints(style_name="dialog_group"),
    )

    assert group.members(registry) == [first, second]
    assert group.content is None
