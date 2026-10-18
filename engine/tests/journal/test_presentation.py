"""Control addresses and pure desired-music reconstruction over canonical intent."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.core import Graph, Registry
from tangl.journal.fragments import (
    ContentFragment,
    ControlFragment,
    GroupFragment,
    MediaFragment,
    fragment_from_dto,
    fragment_to_dto,
)
from tangl.journal.presentation import desired_music
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.persistence.structuring import StructuringHandler
from tangl.presentation.hints import StagingHints
from tangl.service.media import media_fragment_to_payload
from tangl.vm import Ledger


def cue(rit: MediaRIT, **kwargs) -> MediaFragment:
    return MediaFragment(content=rit, content_format="rit", **{"media_role": "music", **kwargs})


def test_targets_distinguish_occurrence_resource_role_and_authored_handle() -> None:
    rit = MediaRIT(data="<svg/>", data_type=MediaDataType.VECTOR)
    bob = cue(rit, media_role="avatar_im", presentation_handle="character:bob")
    # Separate uses of one resource are not the same character or occurrence.
    other = bob.evolve(uid=uuid4(), presentation_handle="character:alice")
    registry = Registry()
    for item in [bob, other, ContentFragment(content="Hello")]:
        registry.add(item)
    transported = Registry()
    for media in [bob, other]:
        transported.add(fragment_from_dto(media_fragment_to_payload(media)))
    cases = [
        ({"kind": "fragment", "fragment_id": bob.uid}, [bob.uid]),
        ({"kind": "rit", "rit_id": rit.uid}, [bob.uid, other.uid]),
        ({"kind": "role", "media_role": "avatar_im"}, [bob.uid, other.uid]),
        ({"kind": "handle", "handle": "character:bob"}, [bob.uid]),
        ({"kind": "fragment", "fragment_id": uuid4()}, []),
        ({"kind": "rit", "rit_id": uuid4()}, []),
        ({"kind": "role", "media_role": "absent"}, []),
        ({"kind": "handle", "handle": "absent"}, []),
    ]
    for target, expected in cases:
        control = ControlFragment(fragment_type="delete", target=target)
        assert [f.uid for f in control.references(registry)] == expected
        assert [f.uid for f in control.references(transported)] == expected
        dto = fragment_to_dto(control)
        restored = fragment_from_dto(dto)
        assert restored.target == control.target
        assert "ref_id" not in dto and "reference_id" not in dto
        canonical = StructuringHandler.structure(
            Json.deserialize(Json.serialize(control.unstructure())),
            kind_map={"ControlFragment": ControlFragment},
        )
        assert canonical.target == control.target


def test_fold_continuity_replacement_stop_restart_and_missing_targets() -> None:
    a = MediaRIT(data=b"track a", data_type=MediaDataType.AUDIO)
    b = MediaRIT(data=b"track b", data_type=MediaDataType.AUDIO)
    first = cue(a, staging_hints=StagingHints(media_timing="loop"))
    restatement = cue(a, source_id=uuid4())
    history = [first, *[ContentFragment(content=f"Block {i}") for i in range(30)],
               GroupFragment(group_type="scene"), restatement]
    restart = ControlFragment(
        target={"kind": "role", "media_role": "music"}, media_action="restart", media=cue(a),
    )
    history.extend([restart, restart])
    before = Json.serialize([f.unstructure() for f in history])
    assert desired_music(history).rit_id == a.uid
    assert desired_music(history).staging_hints.media_timing == "loop"
    assert Json.serialize([f.unstructure() for f in history]) == before
    history.append(cue(b))
    assert desired_music(history).rit_id == b.uid
    history.append(ControlFragment(fragment_type="delete", target={"kind": "rit", "rit_id": a.uid}))
    assert desired_music(history).rit_id == b.uid
    history.append(ControlFragment(
        fragment_type="delete", target={"kind": "role", "media_role": "music"},
    ))
    assert desired_music(history) is None
    history.append(first.evolve(uid=uuid4()))
    assert desired_music(history).rit_id == a.uid


def test_restart_media_and_targets_survive_real_json_ledger_restore() -> None:
    graph = Graph()
    start = graph.add_node(label="start")
    rit = MediaRIT(data=b"track", data_type=MediaDataType.AUDIO)
    graph.add(rit)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    first = cue(rit, staging_hints=StagingHints(media_timing="loop"))
    restart = ControlFragment(
        target={"kind": "role", "media_role": "music"}, media_action="restart", media=cue(rit),
    )
    ledger.output_stream.extend([first, restart])
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    records = list(restored.output_stream.values())
    restored_control = next(f for f in records if isinstance(f, ControlFragment))
    assert restored_control.media.content is restored.graph.get(rit.uid)
    assert restored_control.uid == restart.uid
    assert desired_music(records).staging_hints.media_timing == "loop"
    assert len(restored.graph.members) == len(graph.members)


def test_restart_requires_an_ordinary_media_descriptor() -> None:
    with pytest.raises(ValueError, match="ordinary media"):
        ControlFragment(target={"kind": "role", "media_role": "music"}, media_action="restart")
    with pytest.raises(ValueError, match="typed media field"):
        ControlFragment(
            target={"kind": "role", "media_role": "music"},
            payload={"media": {"path": "/backend/music.wav"}},
        )


@pytest.mark.parametrize("kind", ["fragment", "rit", "role", "handle"])
def test_music_stop_matches_all_target_meanings_and_absent_is_noop(kind: str) -> None:
    rit = MediaRIT(data=b"track", data_type=MediaDataType.AUDIO)
    first = cue(rit, presentation_handle="island:theme")
    target = {
        "fragment": {"kind": kind, "fragment_id": first.uid},
        "rit": {"kind": kind, "rit_id": rit.uid},
        "role": {"kind": kind, "media_role": "music"},
        "handle": {"kind": kind, "handle": "island:theme"},
    }[kind]
    control = ControlFragment(fragment_type="delete", target=target)
    assert desired_music([first, control]) is None
    assert desired_music([control]) is None


def test_media_patch_is_derived_without_mutating_journal() -> None:
    rit = MediaRIT(data=b"track", data_type=MediaDataType.AUDIO)
    first = cue(rit)
    control = ControlFragment(
        target={"kind": "fragment", "fragment_id": first.uid}, payload={"text": "A new caption"},
    )
    assert desired_music([first, control]).text == "A new caption"
    assert "text" not in fragment_to_dto(first)
