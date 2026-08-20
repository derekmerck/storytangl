"""One presentation-safe credential card through ordinary media provisioning."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from lxml import etree
import pytest

from tangl.core import Graph, Selector, TokenCatalog
from tangl.journal.fragments import GroupFragment, MediaFragment, PieceFragment
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.media_provisioning import MediaSpecProvisioner
from tangl.media.media_resource.media_resource_inv_tag import MediaRITStatus
from tangl.media.media_creators.svg_text_forge import SvgTextSpec
from tangl.mechanics.credentials import (
    CredentialDefinition,
    CredentialStatus,
    CredentialToken,
    Indication,
    Region,
    credential_card_composition_spec,
    credential_card_portrait_spec,
    credential_card_text_spec,
    materialize_packet,
)
from tangl.mechanics.games import CredentialsGame, CredentialsGameHandler, HasGame
from tangl.mechanics.games.handlers import process_game_move, provision_game_moves
from tangl.mechanics.games.credentials_game import (
    CredentialCase,
    CredentialDisposition,
    CredentialsMove,
)
from tangl.mechanics.presence.look import HairColor, Look
from tangl.story import Action, Block
from tangl.story.fabula import World
from tangl.vm import Frame, ResolutionPhase


@pytest.fixture(autouse=True)
def clear_credential_definitions():
    CredentialDefinition.clear_instances()
    yield
    CredentialDefinition.clear_instances()


class _CredentialsBlock(HasGame, Block):
    _game_class = CredentialsGame
    _game_handler_class = CredentialsGameHandler


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        return root if story_id is None else root / str(story_id)

    return _resolve


def _case(
    *,
    status: CredentialStatus = CredentialStatus.VALID,
    candidate_name: str = "Ada Venn",
    definition_label: str = "card-id",
) -> CredentialCase:
    definition = CredentialDefinition(
        label=definition_label,
        name="Border Pass",
        indication=Indication.TRAVEL,
        document_kind="id",
        issuer_group="border_control",
        valid_period=0,
    )
    return CredentialCase(
        candidate_name=candidate_name,
        presented_documents={"passport": "An identity document."},
        packet_manager=materialize_packet(
            owner=object(),
            region=Region.LOCAL,
            purpose=Indication.TRAVEL,
            id_card=CredentialToken(indication=Indication.TRAVEL, status=status),
            credentials=[],
            possessions=[],
            label_prefix="Ada Venn",
            catalog=TokenCatalog(
                wst=CredentialDefinition,
                label="card",
                members=(definition,),
            ),
        ),
    )


def _live_card_case(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    status: CredentialStatus = CredentialStatus.VALID,
    roster: list[CredentialCase] | None = None,
):
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )
    world = World.from_script_data(
        script_data={
            "label": "credential-card-world",
            "scenes": {"intro": {"blocks": {"start": {"content": "Checkpoint"}}}},
        }
    )
    story = world.create_story("credential-card-story").graph
    block = story.add_node(
        kind=_CredentialsBlock,
        label="checkpoint",
        game_state=CredentialsGame(roster=roster or [_case(status=status)]),
    )
    handler = block.game_handler
    handler.setup(block.game)
    projection = handler.credential_card_projections(block.game)[0]
    return story, block, block.game.active_case.packet_manager, projection


def _context(story, block):
    return SimpleNamespace(
        graph=story,
        cursor=block,
        cursor_id=block.uid,
        get_ns=lambda _parent: {},
    )


def _provision(story, block, spec):
    dependency = MediaDep(registry=story, predecessor_id=block.uid, media_spec=spec)
    story.add(dependency)
    offers = list(
        MediaSpecProvisioner(graph=story).get_dependency_offers(
            dependency.requirement,
            _ctx=_context(story, block),
        )
    )
    assert len(offers) == 1
    rit = offers[0].callback(_ctx=_context(story, block))
    story.add(rit)
    return rit


def test_card_specs_use_document_subject_and_safe_ordered_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block, packet, projection = _live_card_case(
        monkeypatch,
        tmp_path,
        status=CredentialStatus.WRONG_HOLDER,
    )
    bearer = packet.resolve_subject(packet.bearer_id)
    subject = packet.resolve_subject(projection.subject_id)
    bearer.look = Look(hair_color=HairColor.RED)
    subject.look = Look(hair_color=HairColor.DARK)

    portrait = credential_card_portrait_spec(projection, subject)
    text = credential_card_text_spec(projection)

    assert story.get(block.uid) is block
    assert projection.subject_id != packet.bearer_id
    assert portrait.identity_key == str(projection.subject_id)
    assert portrait.media_role == "id_photo"
    assert portrait.traits != bearer.adapt_look_media_spec().traits
    assert text.lines == (
        projection.document_label,
        projection.bearer_label,
        *(part.content for part in projection.visible_parts),
    )
    payload = json.dumps(
        {"portrait": portrait.normalized_spec_payload(), "text": text.normalized_spec_payload()},
        default=str,
    )
    assert CredentialStatus.WRONG_HOLDER.value not in payload
    assert "DiceBear" not in Path(__file__).parents[3].joinpath(
        "src/tangl/mechanics/credentials/card_media.py"
    ).read_text()
    with pytest.raises(ValueError, match="does not match projection"):
        credential_card_portrait_spec(projection, bearer)


def test_card_composition_provisions_and_reuses_children_and_parent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block, packet, projection = _live_card_case(monkeypatch, tmp_path)
    subject = packet.resolve_subject(projection.subject_id)
    portrait_spec = credential_card_portrait_spec(projection, subject)
    text_spec = credential_card_text_spec(projection)
    portrait_rit = _provision(story, block, portrait_spec)
    text_rit = _provision(story, block, text_spec)
    reused_portrait = _provision(story, block, portrait_spec)
    reused_text = _provision(story, block, text_spec)
    composition = credential_card_composition_spec(
        portrait_rit=portrait_rit,
        text_rit=text_rit,
    )
    card_rit = _provision(story, block, composition)
    reused = _provision(
        story,
        block,
        credential_card_composition_spec(
            portrait_rit=portrait_rit,
            text_rit=text_rit,
        ),
    )

    assert portrait_rit.uid == reused_portrait.uid
    assert text_rit.uid == reused_text.uid
    assert card_rit.uid == reused.uid
    assert card_rit.status.value == "resolved"
    assert card_rit.data_type is MediaDataType.VECTOR
    assert card_rit.path is not None
    root = etree.fromstring(card_rit.path.read_bytes())
    lines = root.xpath(".//svg:text", namespaces={"svg": "http://www.w3.org/2000/svg"})
    adapted_text = text_spec.adapt_spec(ctx={})
    assert isinstance(adapted_text, SvgTextSpec)
    assert [line.text for line in lines] == list(adapted_text.lines)
    assert adapted_text.canvas_height <= 176
    assert [item.role for item in composition.inputs] == ["portrait", "printable_text"]
    assert [item.offset for item in composition.inputs] == [(16, 32), (176, 16)]
    assert composition.canvas_size == (512, 192)
    assert composition.background == "white"
    assert composition.treatment == "credential_id_card"
    assert card_rit.derivation_spec == composition.normalized_spec_payload()
    assert card_rit.adapted_spec is not None
    assert card_rit.execution_spec is not None


def test_card_composition_requires_resolved_child_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _live_card_case(monkeypatch, tmp_path)
    pending = MediaRIT(
        label="pending-portrait",
        status=MediaRITStatus.PENDING,
        data_type=MediaDataType.VECTOR,
    )
    text = MediaRIT(label="text", data="<svg/>", data_type=MediaDataType.VECTOR)

    with pytest.raises(ValueError, match="requires resolved child content"):
        credential_card_composition_spec(portrait_rit=pending, text_rit=text)


def test_card_identity_uses_visible_children_not_component_or_rit_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, _, packet, projection = _live_card_case(monkeypatch, tmp_path)
    subject = packet.resolve_subject(projection.subject_id)
    portrait = credential_card_portrait_spec(projection, subject)
    text = credential_card_text_spec(projection)
    equivalent_projection = projection.model_copy(update={"component_id": uuid4()})
    first_portrait = MediaRIT(label="portrait-one", data="<svg/>", data_type=MediaDataType.VECTOR)
    first_text = MediaRIT(label="text-one", data="<svg>text</svg>", data_type=MediaDataType.VECTOR)
    second_portrait = MediaRIT(label="portrait-two", data="<svg/>", data_type=MediaDataType.VECTOR)
    second_text = MediaRIT(label="text-two", data="<svg>text</svg>", data_type=MediaDataType.VECTOR)
    first = credential_card_composition_spec(
        portrait_rit=first_portrait,
        text_rit=first_text,
    )
    equivalent = credential_card_composition_spec(
        portrait_rit=second_portrait,
        text_rit=second_text,
    )
    changed = credential_card_text_spec(
        projection.model_copy(update={"document_label": "student ID"})
    )
    changed_text_rit = MediaRIT(
        label="text-changed",
        data="<svg>student ID</svg>",
        data_type=MediaDataType.VECTOR,
    )
    changed_parent = credential_card_composition_spec(
        portrait_rit=first_portrait,
        text_rit=changed_text_rit,
    )

    assert portrait.spec_fingerprint() == credential_card_portrait_spec(
        equivalent_projection,
        subject,
    ).spec_fingerprint()
    assert text.spec_fingerprint() == credential_card_text_spec(equivalent_projection).spec_fingerprint()
    assert first.spec_fingerprint() == equivalent.spec_fingerprint()
    assert text.spec_fingerprint() != changed.spec_fingerprint()
    assert first.spec_fingerprint() != changed_parent.spec_fingerprint()
    assert first.normalized_spec_payload()["inputs"][0]["rit_id"] == first_portrait.uid


def test_complete_replacement_has_no_card_media_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block, _, _ = _live_card_case(monkeypatch, tmp_path)
    block.game.active_case.presented_documents = {"passport": "An authored replacement."}

    assert block.game_handler.credential_card_projections(block.game) == []
    assert story.get(block.uid) is block


def test_lifecycle_provisions_one_card_and_emits_stable_piece_media_relation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block, _, projection = _live_card_case(monkeypatch, tmp_path)
    ctx = Frame(graph=story, cursor=block)._make_ctx()

    assert not any(
        isinstance(fragment, MediaFragment)
        for fragment in block.game_handler.get_journal_fragments(block.game, ctx=ctx)
    )
    ctx.current_phase = ResolutionPhase.PLANNING
    assert provision_game_moves(cursor=block, ctx=ctx) is None
    first = block.game_handler.get_journal_fragments(block.game, ctx=ctx)
    block.game_handler.provision_presentation(block.game, ctx=ctx)
    second = block.game_handler.get_journal_fragments(block.game, ctx=ctx)

    dependencies = [value for value in story.values() if isinstance(value, MediaDep)]
    rits = [value for value in story.values() if isinstance(value, MediaRIT)]
    assert [dependency.label for dependency in dependencies] == [
        "credential-card-portrait",
        "credential-card-printable_text",
        "credential-card-card",
    ]
    assert {dependency.predecessor_id for dependency in dependencies} == {block.uid}
    assert len(rits) == 3

    document = next(
        fragment
        for fragment in first
        if isinstance(fragment, PieceFragment)
        and fragment.properties.get("component_id") == projection.component_id
    )
    media = [fragment for fragment in first if isinstance(fragment, MediaFragment)]
    relation = [
        fragment
        for fragment in first
        if isinstance(fragment, GroupFragment) and fragment.group_type == "piece_media"
    ]
    assert len(media) == 1
    assert media[0].source_id == projection.component_id
    assert media[0].content_format == "rit"
    assert len(relation) == 1
    assert relation[0].member_ids == [document.uid, media[0].uid]
    assert [fragment.uid for fragment in second if isinstance(fragment, MediaFragment)] == [
        media[0].uid
    ]
    assert [
        fragment.uid
        for fragment in second
        if isinstance(fragment, GroupFragment) and fragment.group_type == "piece_media"
    ] == [relation[0].uid]


def test_frontier_card_dependencies_are_owned_by_the_credential_block(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block, _, _ = _live_card_case(monkeypatch, tmp_path)
    entry = story.add_node(kind=Block, label="entry")
    action = Action(
        graph=story,
        predecessor_id=entry.uid,
        successor_id=block.uid,
        label="Enter checkpoint",
    )

    Frame(graph=story, cursor=entry).follow_edge(action)

    dependencies = [value for value in story.values() if isinstance(value, MediaDep)]
    assert {dependency.predecessor_id for dependency in dependencies} == {block.uid}


def test_lifecycle_uses_document_subject_and_keeps_text_when_card_inputs_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block, packet, projection = _live_card_case(
        monkeypatch,
        tmp_path,
        status=CredentialStatus.WRONG_HOLDER,
    )
    ctx = Frame(graph=story, cursor=block)._make_ctx()
    block.game_handler.provision_presentation(block.game, ctx=ctx)
    portrait = next(
        dependency
        for dependency in story.values()
        if isinstance(dependency, MediaDep) and dependency.label == "credential-card-portrait"
    )
    text = next(
        dependency
        for dependency in story.values()
        if isinstance(dependency, MediaDep) and dependency.label == "credential-card-printable_text"
    )

    assert portrait.provider.derivation_spec["identity_key"] == str(projection.subject_id)
    assert projection.subject_id != packet.bearer_id
    text.provider.status = MediaRITStatus.PENDING
    pending = block.game_handler.get_journal_fragments(block.game, ctx=ctx)
    assert any(isinstance(fragment, PieceFragment) for fragment in pending)
    assert not any(isinstance(fragment, MediaFragment) for fragment in pending)

    text.provider.status = MediaRITStatus.FAILED
    failed = block.game_handler.get_journal_fragments(block.game, ctx=ctx)
    assert any(isinstance(fragment, PieceFragment) for fragment in failed)
    assert not any(isinstance(fragment, MediaFragment) for fragment in failed)

    text.provider.status = MediaRITStatus.RESOLVED
    text.provider.data = "<svg/>"
    text.provider.path = None
    stale = block.game_handler.get_journal_fragments(block.game, ctx=ctx)
    assert any(isinstance(fragment, PieceFragment) for fragment in stale)
    assert not any(isinstance(fragment, MediaFragment) for fragment in stale)


def test_lifecycle_keeps_text_when_parent_card_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block, _, _ = _live_card_case(monkeypatch, tmp_path)
    ctx = Frame(graph=story, cursor=block)._make_ctx()
    block.game_handler.provision_presentation(block.game, ctx=ctx)
    card = next(
        dependency
        for dependency in story.values()
        if isinstance(dependency, MediaDep) and dependency.label == "credential-card-card"
    )

    card.provider.status = MediaRITStatus.PENDING
    pending = block.game_handler.get_journal_fragments(block.game, ctx=ctx)
    assert any(isinstance(fragment, PieceFragment) for fragment in pending)
    assert not any(isinstance(fragment, MediaFragment) for fragment in pending)
    assert not any(
        isinstance(fragment, GroupFragment) and fragment.group_type == "piece_media"
        for fragment in pending
    )

    card.provider.status = MediaRITStatus.FAILED
    failed = block.game_handler.get_journal_fragments(block.game, ctx=ctx)
    assert any(isinstance(fragment, PieceFragment) for fragment in failed)
    assert not any(isinstance(fragment, MediaFragment) for fragment in failed)


def test_lifecycle_provisions_the_next_candidate_during_update(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first_case = _case(candidate_name="Ada Venn", definition_label="card-id-one")
    second_case = _case(candidate_name="Bea Moss", definition_label="card-id-two")
    story, block, _, _ = _live_card_case(
        monkeypatch,
        tmp_path,
        roster=[first_case, second_case],
    )
    frame = Frame(graph=story, cursor=block)
    action = Action(
        graph=story,
        predecessor_id=block.uid,
        successor_id=block.uid,
        payload={"move": CredentialsMove(kind="decide", target=CredentialDisposition.PASS.value)},
    )
    frame.selected_edge = action
    ctx = frame._make_ctx(incoming_edge=action, incoming_payload=action.payload)

    ctx.current_phase = ResolutionPhase.PLANNING
    provision_game_moves(cursor=block, ctx=ctx)
    next_projection = block.game_handler.credential_card_projections(block.game, case=second_case)[0]
    prepared_dependency_ids = {
        dependency.uid for dependency in story.values() if isinstance(dependency, MediaDep)
    }
    active_journal = block.game_handler.get_journal_fragments(block.game, ctx=ctx)

    assert block.game.case_index == 0
    assert block.game.active_case is first_case
    assert block.game.to_namespace()["credential_candidate_name"] == "Ada Venn"
    assert len(prepared_dependency_ids) == 6
    assert not any(
        isinstance(fragment, MediaFragment) and fragment.source_id == next_projection.component_id
        for fragment in active_journal
    )
    assert all("Bea Moss" not in str(fragment.content) for fragment in active_journal)

    ctx.current_phase = ResolutionPhase.UPDATE
    process_game_move(block, ctx=ctx)

    assert block.game.case_index == 1
    journal = block.game_handler.get_journal_fragments(block.game, ctx=ctx)
    assert {
        dependency.uid for dependency in story.values() if isinstance(dependency, MediaDep)
    } == prepared_dependency_ids
    assert any(
        isinstance(fragment, MediaFragment) and fragment.source_id == next_projection.component_id
        for fragment in journal
    )


def test_lifecycle_replacement_suppresses_previously_provisioned_card_media(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block, _, _ = _live_card_case(monkeypatch, tmp_path)
    ctx = Frame(graph=story, cursor=block)._make_ctx()
    block.game_handler.provision_presentation(block.game, ctx=ctx)
    block.game.active_case.presented_documents = {"passport": "An authored replacement."}

    fragments = block.game_handler.get_journal_fragments(block.game, ctx=ctx)

    assert not any(isinstance(fragment, MediaFragment) for fragment in fragments)
    assert any(
        isinstance(fragment, PieceFragment) and fragment.content == "An authored replacement."
        for fragment in fragments
    )


def test_lifecycle_round_trip_preserves_card_dependencies_and_fragment_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block, _, _ = _live_card_case(monkeypatch, tmp_path)
    ctx = Frame(graph=story, cursor=block)._make_ctx()
    block.game_handler.provision_presentation(block.game, ctx=ctx)
    original = next(
        fragment
        for fragment in block.game_handler.get_journal_fragments(block.game, ctx=ctx)
        if isinstance(fragment, MediaFragment)
    )

    restored = Graph.structure(story.unstructure())
    restored_block = restored.find_one(Selector(label="checkpoint"))
    restored_ctx = Frame(graph=restored, cursor=restored_block)._make_ctx()
    restored_block.game_handler.provision_presentation(restored_block.game, ctx=restored_ctx)
    restored_media = [
        fragment
        for fragment in restored_block.game_handler.get_journal_fragments(
            restored_block.game,
            ctx=restored_ctx,
        )
        if isinstance(fragment, MediaFragment)
    ]

    assert len([value for value in restored.values() if isinstance(value, MediaDep)]) == 3
    assert [fragment.uid for fragment in restored_media] == [original.uid]
