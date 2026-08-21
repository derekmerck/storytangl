"""Tests for graph-owned phrase badge repertoires."""

from __future__ import annotations

from typing import Self

import pytest
from pydantic import Field, model_validator

from tangl.core import Graph, Node, TokenCatalog
from tangl.mechanics.games import (
    KNOWN_PHRASES_SLOT,
    PhraseBadge,
    PhraseType,
    RepertoireManager,
)
from tangl.mechanics.transaction import (
    AssetMoveCommitment,
    ComponentSlotAssetHolder,
    TransactionOffer,
)


@pytest.fixture(autouse=True)
def reset_phrase_types() -> None:
    """Keep the singleton catalog local to each repertoire test."""

    PhraseType.clear_instances()
    yield
    PhraseType.clear_instances()


class RepertoireOwner(Node):
    """Test-only graph owner embedding the ordinary repertoire manager."""

    repertoire: RepertoireManager = Field(
        default_factory=RepertoireManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @model_validator(mode="after")
    def _bind_repertoire_owner(self) -> Self:
        self.repertoire.bind_owner(self)
        return self


def phrase_type(label: str, text: str) -> PhraseType:
    """Create one dual-role phrase definition for a focused test."""

    return PhraseType(label=label, text=text, roles=("call", "response"))


def test_phrase_catalogs_remain_explicitly_bounded() -> None:
    first = phrase_type("first", "First phrase")
    second = phrase_type("second", "Second phrase")
    third = phrase_type("third", "Third phrase")

    first_catalog = TokenCatalog(PhraseType, members=(first, second))
    second_catalog = TokenCatalog(PhraseType, members=(third,))

    assert [phrase.label for phrase in first_catalog.find_all()] == ["first", "second"]
    assert [phrase.label for phrase in second_catalog.find_all()] == ["third"]
    assert {phrase.label for phrase in PhraseType.all_instances()} == {
        "first",
        "second",
        "third",
    }


def test_repertoire_graph_roundtrip_rebinds_badge_and_owner() -> None:
    definition = phrase_type("riposte", "You fight like a dairy farmer!")
    graph = Graph()
    owner = graph.add_node(kind=RepertoireOwner, label="player")
    badge = graph.add_node(
        kind=PhraseBadge,
        label="player-riposte",
        token_from=definition.label,
    )
    owner.repertoire.assign(KNOWN_PHRASES_SLOT, badge)

    restored = Graph.structure(graph.unstructure())
    restored_owner = restored.get(owner.uid)
    restored_badge = restored.get(badge.uid)

    assert isinstance(restored_owner, RepertoireOwner)
    assert isinstance(restored_badge, PhraseBadge)
    assert isinstance(restored_owner.repertoire, RepertoireManager)
    assert restored_owner.repertoire.owner is restored_owner
    assert restored_owner.repertoire.assignment_ids == {
        KNOWN_PHRASES_SLOT: [badge.uid],
    }
    assert restored_owner.repertoire.badges() == [restored_badge]
    assert restored_badge.token_from == definition.label
    assert restored_badge.reference_singleton is definition
    assert restored_owner.repertoire.phrase_ids() == [definition.label]
    assert restored_owner.repertoire.has_phrase(definition.label)


def test_phrase_badge_transfers_between_repertoires_and_roundtrips() -> None:
    definition = phrase_type("counter", "How appropriate. You fight like a cow.")
    graph = Graph()
    giver = graph.add_node(kind=RepertoireOwner, label="giver")
    receiver = graph.add_node(kind=RepertoireOwner, label="receiver")
    badge = graph.add_node(
        kind=PhraseBadge,
        label="counter-badge",
        token_from=definition.label,
    )
    giver.repertoire.assign(KNOWN_PHRASES_SLOT, badge)

    offer = TransactionOffer(
        label="transfer phrase badge",
        commitments=[
            AssetMoveCommitment(
                ComponentSlotAssetHolder(giver.repertoire, KNOWN_PHRASES_SLOT),
                ComponentSlotAssetHolder(receiver.repertoire, KNOWN_PHRASES_SLOT),
                badge,
            ),
        ],
    )

    receipt = offer.accept()

    assert receipt.offer_label == "transfer phrase badge"
    assert giver.repertoire.badges() == []
    assert receiver.repertoire.badges() == [badge]

    restored = Graph.structure(graph.unstructure())
    restored_giver = restored.get(giver.uid)
    restored_receiver = restored.get(receiver.uid)
    restored_badge = restored.get(badge.uid)

    assert isinstance(restored_giver, RepertoireOwner)
    assert isinstance(restored_receiver, RepertoireOwner)
    assert isinstance(restored_badge, PhraseBadge)
    assert restored_giver.repertoire.owner is restored_giver
    assert restored_receiver.repertoire.owner is restored_receiver
    assert restored_giver.repertoire.badges() == []
    assert restored_receiver.repertoire.badges() == [restored_badge]
    assert restored_badge.uid == badge.uid
    assert restored_badge.reference_singleton is definition
