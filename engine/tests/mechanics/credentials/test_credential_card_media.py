"""One presentation-safe credential card through ordinary media provisioning."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from lxml import etree
import pytest

from tangl.core import TokenCatalog
from tangl.media import MediaDataType
from tangl.media.media_creators.composition_forge.composition_spec import CompositionSpec
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.media_provisioning import MediaSpecProvisioner
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
from tangl.mechanics.games.credentials_game import CredentialCase
from tangl.mechanics.presence.look import HairColor, Look
from tangl.story import Block
from tangl.story.fabula import World


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


def _case(*, status: CredentialStatus = CredentialStatus.VALID) -> CredentialCase:
    definition = CredentialDefinition(
        label="card-id",
        name="Border Pass",
        indication=Indication.TRAVEL,
        document_kind="id",
        issuer_group="border_control",
        valid_period=0,
    )
    return CredentialCase(
        candidate_name="Ada Venn",
        presented_documents={"passport": "An identity document."},
        packet_manager=materialize_packet(
            owner=object(),
            region=Region.LOCAL,
            purpose=Indication.TRAVEL,
            id_card=CredentialToken(indication=Indication.TRAVEL, status=status),
            credentials=[],
            possessions=[],
            label_prefix="Ada Venn",
            catalog=TokenCatalog(wst=CredentialDefinition, label="card", members=(definition,)),
        ),
    )


def _live_card_case(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    status: CredentialStatus = CredentialStatus.VALID,
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
        game_state=CredentialsGame(roster=[_case(status=status)]),
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
    composition = credential_card_composition_spec(
        projection,
        portrait_rit=portrait_rit,
        text_rit=text_rit,
    )
    card_rit = _provision(story, block, composition)
    reused = _provision(
        story,
        block,
        credential_card_composition_spec(
            projection,
            portrait_rit=portrait_rit,
            text_rit=text_rit,
        ),
    )

    assert card_rit.uid == reused.uid
    assert card_rit.status.value == "resolved"
    assert card_rit.data_type is MediaDataType.VECTOR
    assert card_rit.path is not None
    root = etree.fromstring(card_rit.path.read_bytes())
    lines = root.xpath(".//svg:text", namespaces={"svg": "http://www.w3.org/2000/svg"})
    assert [line.text for line in lines] == list(text_spec.lines)
    assert [item.role for item in composition.inputs] == ["portrait", "printable_text"]
    assert [item.offset for item in composition.inputs] == [(16, 32), (176, 16)]
    assert composition.canvas_size == (512, 192)
    assert composition.background == "white"
    assert composition.treatment == "credential_id_card"
    assert card_rit.derivation_spec == composition.normalized_spec_payload()
    assert card_rit.adapted_spec is not None
    assert card_rit.execution_spec is not None


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
        projection,
        portrait_rit=first_portrait,
        text_rit=first_text,
    )
    equivalent = credential_card_composition_spec(
        equivalent_projection,
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
        projection.model_copy(update={"document_label": "student ID"}),
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
