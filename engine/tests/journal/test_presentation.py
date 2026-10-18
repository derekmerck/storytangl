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
        patch_kind="presentation",
    )
    assert desired_music([first, control]).text == "A new caption"
    assert "text" not in fragment_to_dto(first)


@pytest.mark.parametrize("payload", [
    {"content_format": "url", "content": "https://example.invalid/track.wav"},
    {"content_format": "path", "content": "/server/private/music.wav"},
    {"url": "https://example.invalid/track.wav"},
    {"path": "/server/private/music.wav"},
    {"rit_id": str(uuid4())},
    {"format": "data", "data": "AA=="},
    {"fragment_type": "media", "content": "a source"},
])
@pytest.mark.parametrize("patch_kind", ["content", "presentation"])
def test_media_transport_payloads_fail_at_control_boundary(payload: dict, patch_kind: str) -> None:
    with pytest.raises(ValueError, match="typed media field"):
        ControlFragment(
            target={"kind": "fragment", "fragment_id": uuid4()},
            payload=payload, patch_kind=patch_kind,
        )


def test_text_game_patch_is_not_reinterpreted_as_a_media_source() -> None:
    first = cue(MediaRIT(data=b"track", data_type=MediaDataType.AUDIO))
    text = ContentFragment(content="Before")
    payload = {"content": "https://example.invalid/ordinary-prose", "data": {"score": 4}}
    text_edit = ControlFragment(
        target={"kind": "fragment", "fragment_id": text.uid}, payload=payload,
    )
    assert text_edit.apply_to(text).content == payload["content"]
    assert text_edit.apply_to(text).data == {"score": 4}
    media_edit = text_edit.evolve(target={"kind": "fragment", "fragment_id": first.uid})
    assert media_edit.apply_to(first) is first
    assert desired_music([first, media_edit]) is first
    with pytest.raises(ValueError, match="only captions"):
        ControlFragment(
            target=media_edit.target, patch_kind="presentation", payload={"content": "a source"},
        )


def test_media_presentation_and_replacement_survive_json_without_changing_occurrence() -> None:
    graph = Graph()
    start = graph.add_node(label="start")
    a = MediaRIT(data=b"a", data_type=MediaDataType.AUDIO)
    b = MediaRIT(data=b"b", data_type=MediaDataType.AUDIO)
    graph.add(a)
    graph.add(b)
    first = cue(
        a, presentation_handle="character:alice", staging_hints=StagingHints(media_timing="loop"),
    )
    move = ControlFragment(
        target={"kind": "handle", "handle": "character:alice"}, patch_kind="presentation",
        payload={"text": "A caption", "staging_hints": {
            "media_x": 0.25, "media_visibility": {"preference_id": "shown", "values": [True]},
        }},
    )
    moved = move.apply_to(first)
    assert moved.uid == first.uid and moved.content is a and moved.rit_id == a.uid
    assert moved.text == "A caption" and moved.staging_hints.media_x == 0.25
    assert moved.staging_hints.media_visibility.values == [True]
    assert moved.staging_hints.media_timing == "loop"
    same = ControlFragment(target=move.target, media=cue(a, presentation_handle="character:alice"))
    assert same.apply_to(moved).staging_hints.media_timing == "loop"
    replacement = ControlFragment(target=move.target, media=cue(b))
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ledger.output_stream.extend([first, move, same, replacement])
    serialized = Json.serialize(ledger.unstructure())
    restored = Ledger.structure(Json.deserialize(serialized))
    records = list(restored.output_stream.values())
    restored_replacement = next(f for f in records if f.uid == replacement.uid)
    restored_move = next(f for f in records if f.uid == move.uid)
    assert restored_move.patch_kind == "presentation" and restored_move.media is None
    assert restored_replacement.media.content is restored.graph.get(b.uid)
    assert restored_replacement.media_action is None
    before_reads = Json.serialize(restored.unstructure())
    restored_first = next(f for f in records if f.uid == first.uid)
    assert restored_move.apply_to(restored_first).content is restored.graph.get(a.uid)
    selected = desired_music(restored.get_journal())
    assert selected.uid == first.uid and selected.rit_id == b.uid
    assert selected.content is restored.graph.get(b.uid)
    assert desired_music([replacement]) is None
    assert replacement.apply_to(ContentFragment(content="Not media")) is not None
    assert len(restored.graph.members) == len(graph.members)
    assert Json.serialize(restored.unstructure()) == before_reads


def test_media_replacement_does_not_require_universal_rit_identity() -> None:
    first = MediaFragment(content="https://example.invalid/a.svg", content_format="url")
    replacement = MediaFragment(content="https://example.invalid/b.svg", content_format="url")
    control = ControlFragment(
        target={"kind": "fragment", "fragment_id": first.uid}, media=replacement,
    )
    updated = control.apply_to(first)
    assert updated.uid == first.uid and updated.content == replacement.content
    assert updated.rit_id is None
    restored = StructuringHandler.structure(
        Json.deserialize(Json.serialize(control.unstructure())),
        kind_map={"ControlFragment": ControlFragment},
    )
    assert restored.media.content == replacement.content and restored.media.rit_id is None
