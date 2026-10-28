"""Casting Desk uses ordinary service choices and constructor-form persistence."""
from __future__ import annotations

from pathlib import Path
from random import Random
import subprocess
import sys
from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest

from tangl.core import Selector
from tangl.journal.fragments import ContentFragment
from tangl.lang.age_range import AgeRange
from tangl.lang.gens import Gens
from tangl.lang.personal_name import PersonalName
from tangl.mechanics.demographics import GenerationRequest, NameBank
from tangl.persistence import PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.service import ServiceManager, world_registry
from tangl.service.response import DirectEdgeRequest, RuntimeEnvelope
from tangl.story import Actor, Scene
from tangl.vm import Ledger, ResolutionPhase
from tangl.vm.dispatch import do_journal, do_update
from tangl.vm.runtime.frame import PhaseCtx

if TYPE_CHECKING:
    from casting_desk.domain import Applicant


WORLDS = Path(__file__).resolve().parents[3] / "worlds"
SLOTS = ("river", "hill", "grove")


@pytest.fixture
def desk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ServiceManager, UUID]:
    monkeypatch.setattr(world_registry, "_DISCOVERED_REGISTRIES", {})
    monkeypatch.setattr(world_registry, "_MANUAL_WORLDS", {})
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [WORLDS])
    manager = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path))
    user_id = UUID(manager.create_user(secret="casting-reader").details["user_id"])
    manager.create_story(user_id=user_id, world_id="casting_desk")
    return manager, user_id


def applicant(ledger: Ledger, slot: str) -> Applicant:
    return cast("Applicant", ledger.graph.find_one(Selector(label=f"{slot}_applicant")))


def choose(manager: ServiceManager, user_id: UUID, label: str) -> RuntimeEnvelope:
    with manager.open_session(user_id=user_id) as session:
        edge = next(session.ledger.cursor.edges_out(Selector(label=label)))
    return manager.resolve_choice(user_id=user_id, request=DirectEdgeRequest(edge_id=edge.uid))


def text(envelope: RuntimeEnvelope) -> str:
    return "\n".join(
        fragment.content for fragment in envelope.fragments
        if isinstance(fragment, ContentFragment)
    )


def values(ledger: Ledger) -> dict[str, dict[str, object]]:
    return {
        slot: {
            "name": applicant(ledger, slot).personal_name.unstructure(),
            "facts": applicant(ledger, slot).demographic.unstructure(),
            "receipt": applicant(ledger, slot).generation_receipt.unstructure(),
        } for slot in SLOTS
    }


def complete_cast(manager: ServiceManager, user_id: UUID) -> None:
    for slot in SLOTS:
        choose(manager, user_id, slot)
        inspection = choose(manager, user_id, "inspect")
        with manager.open_session(user_id=user_id) as session:
            actor = applicant(session.ledger, slot)
            assert f"Applicant: {actor.personal_name.forms()['full']}." in text(inspection)
            assert f"Origin: {actor.generation_receipt.origin}." in text(inspection)
        choose(manager, user_id, "return")


def test_service_walkthrough_preserves_authored_values_and_targeted_completion(
    desk: tuple[ServiceManager, UUID],
) -> None:
    manager, user_id = desk
    with manager.open_session(user_id=user_id) as session:
        initial_ids = {slot: applicant(session.ledger, slot).uid for slot in SLOTS}
        assert all(applicant(session.ledger, slot).generation_receipt is None for slot in SLOTS)
        assert len(list(session.ledger.graph.find_all(Selector(has_kind=Actor)))) == 3
    choose(manager, user_id, "river")
    with manager.open_session(user_id=user_id) as session:
        assert applicant(session.ledger, "river").generation_receipt is not None
        assert applicant(session.ledger, "hill").generation_receipt is None
        assert applicant(session.ledger, "grove").generation_receipt is None
    choose(manager, user_id, "return")
    complete_cast(manager, user_id)
    with manager.open_session(user_id=user_id) as session:
        river, hill, grove = (applicant(session.ledger, slot) for slot in SLOTS)
        assert river.personal_name.given_name == "Ari"
        assert river.demographic.age_range is AgeRange.MID
        assert river.generation_receipt.generated == ["gender", "family_name"]
        assert hill.personal_name.family_name is None
        assert hill.demographic.gender is Gens.X_
        assert hill.generation_receipt.generated == ["age_range", "given_name"]
        assert river.generation_receipt.origin == "River Guild"
        assert hill.generation_receipt.origin == "Hill Guild"
        assert river.generation_receipt.bank is hill.generation_receipt.bank
        assert river.generation_receipt.bank is NameBank.get_instance("fra")
        assert river.generation_receipt.revision == "sample-v1"
        assert grove.demographic.unstructure() == {"kind": type(grove.demographic)}
        assert grove.generation_receipt.generated == ["given_name", "family_name"]
        assert grove.generation_receipt.bank is NameBank.get_instance("casting_desk.sprite")
        form = grove.generation_receipt.bank.forms["plain"]
        assert grove.personal_name.given_name in form.given.pool.candidates
        assert grove.personal_name.family_name in {
            stem + suffix for stem in form.family.pool.candidates
            for suffix in form.family.suffix.candidates
        }
        saved = values(session.ledger)
    complete_cast(manager, user_id)
    with manager.open_session(user_id=user_id) as session:
        assert values(session.ledger) == saved
        assert {slot: applicant(session.ledger, slot).uid for slot in SLOTS} == initial_ids
        assert len(list(session.ledger.graph.find_all(Selector(has_kind=Actor)))) == 3
    assert "desk closes" in text(choose(manager, user_id, "close"))


def test_matching_supplied_rng_reproduces_values_and_post_draw_state(
    desk: tuple[ServiceManager, UUID],
) -> None:
    manager, user_id = desk
    world = manager.open_world("casting_desk")
    results = []
    for index in range(2):
        graph = world.create_story(f"controlled-{index}").graph
        ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
        rng = Random(11)
        before = rng.getstate()
        for slot in SLOTS:
            scene = graph.find_one(Selector(label=slot, has_kind=Scene))
            block = graph.get(scene.source_id)
            ctx = PhaseCtx(
                graph=graph, cursor_id=block.uid, current_phase=ResolutionPhase.UPDATE,
                random=rng,
            )
            do_update(block, ctx=ctx)
        assert rng.getstate() != before
        results.append((values(ledger), rng.getstate()))
    assert results[0] == results[1]


@pytest.mark.parametrize("seed", [11, 29])
@pytest.mark.parametrize("empty_request", [False, True])
def test_authored_first_completion_preserves_supplied_rng(
    desk: tuple[ServiceManager, UUID], seed: int, empty_request: bool,
) -> None:
    manager, _user_id = desk
    graph = manager.open_world("casting_desk").create_story("authored").graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    actor = applicant(ledger, "river")
    actor.personal_name = PersonalName(given_name="Fixed", family_name="Value", title="")
    actor.demographic.gender = Gens.X_
    if empty_request:
        actor.generation_request = GenerationRequest()
    scene = graph.find_one(Selector(label="river", has_kind=Scene))
    block = graph.get(scene.source_id)
    rng = Random(seed)
    before = rng.getstate()
    ctx = PhaseCtx(
        graph=graph, cursor_id=block.uid, current_phase=ResolutionPhase.UPDATE, random=rng,
    )
    do_update(block, ctx=ctx)
    assert actor.generation_receipt.generated == []
    assert rng.getstate() == before
    do_update(block, ctx=ctx)
    assert rng.getstate() == before


def test_getters_journal_and_completed_update_preserve_rng_and_read_current_name(
    desk: tuple[ServiceManager, UUID],
) -> None:
    manager, user_id = desk
    choose(manager, user_id, "grove")
    with manager.open_session(user_id=user_id) as session:
        ledger = session.ledger
        actor = applicant(ledger, "grove")
        rng = Random(73)
        ctx = PhaseCtx(
            graph=ledger.graph, cursor_id=ledger.cursor_id,
            current_phase=ResolutionPhase.UPDATE, random=rng,
        )
        before = rng.getstate()
        original_receipt = actor.generation_receipt.unstructure()
        actor.personal_name = PersonalName(given_name="New", family_name="Leaf", title="")
        assert actor.get_ns()["full_name"] == "New Leaf"
        assert ctx.get_ns()["applicant_full_name"] == "New Leaf"
        do_update(ledger.cursor, ctx=ctx)
        ctx.current_phase = ResolutionPhase.JOURNAL
        fragments = do_journal(ledger.cursor, ctx=ctx)
        assert any(
            isinstance(fragment, ContentFragment)
            and "Application ready: New Leaf." in fragment.content
            for fragment in fragments
        )
        inspection = next(ledger.cursor.edges_out(Selector(label="inspect"))).successor
        fragments = do_journal(inspection, ctx=ctx.derive(cursor_id=inspection.uid))
        assert any(
            isinstance(fragment, ContentFragment) and "Applicant: New Leaf." in fragment.content
            for fragment in fragments
        )
        assert actor.generation_receipt.unstructure() == original_receipt
        assert rng.getstate() == before


def test_cold_json_service_restore_and_continued_choices_never_resample(
    desk: tuple[ServiceManager, UUID], tmp_path: Path,
) -> None:
    manager, user_id = desk
    complete_cast(manager, user_id)
    with manager.open_session(user_id=user_id) as session:
        expected = {
            "values": values(session.ledger),
            "ids": {slot: applicant(session.ledger, slot).uid for slot in SLOTS},
        }
    expected_path = tmp_path / "expected.json"
    expected_path.write_text(Json.serialize(expected), encoding="utf-8")
    code = '''
from pathlib import Path
import sys
from unittest.mock import patch
from uuid import UUID
from tangl.core import Selector
from tangl.mechanics.demographics import NameBank
from tangl.persistence import PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.service import ServiceManager
from tangl.service.response import DirectEdgeRequest
from tangl.story import World

assert World.get_instance("casting_desk") is None
assert NameBank.get_instance("casting_desk.sprite") is None
manager = ServiceManager(PersistenceManagerFactory.json_file(base_path=Path(sys.argv[1])))
expected = Json.deserialize(Path(sys.argv[3]).read_text())
user = UUID(sys.argv[2])
def check(ledger):
    for slot, saved in expected["values"].items():
        actor = ledger.graph.find_one(Selector(label=slot+"_applicant"))
        assert actor.uid == expected["ids"][slot]
        actual = {
            "name": actor.personal_name.unstructure(),
            "facts": actor.demographic.unstructure(),
            "receipt": actor.generation_receipt.unstructure(),
        }
        assert Json.deserialize(Json.serialize(actual)) == saved
        bank = "casting_desk.sprite" if slot == "grove" else "fra"
        assert actor.generation_receipt.bank is NameBank.get_instance(bank)
with patch("tangl.mechanics.demographics.complete_generation",
           side_effect=AssertionError("resampled")):
    for label in ("river", "inspect", "reread", "return", "hill", "inspect", "return",
                  "grove", "inspect", "return"):
        with manager.open_session(user_id=user) as session:
            check(session.ledger)
            edge = next(session.ledger.cursor.edges_out(Selector(label=label)))
        manager.resolve_choice(user_id=user, request=DirectEdgeRequest(edge_id=edge.uid))
    with manager.open_session(user_id=user) as session:
        check(session.ledger)
'''
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), str(user_id), str(expected_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
