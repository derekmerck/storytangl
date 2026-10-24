"""Optional non-Actor personal names through UPDATE, JSON restoration and replay."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import Field

from tangl.core import BehaviorRegistry, EntityTemplate, Selector
from tangl.journal.fragments import AttributedFragment, ContentFragment
from tangl.lang.personal_name import Gender, PersonalName
from tangl.persistence import PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.prose.naming import (
    NamedActor, NamedConcept, NamingOperations, PersonalNamedActor, PersonalNamedConcept,
    ProseBlock, naming_dispatch,
)
from tangl.service import ServiceManager
from tangl.service.response import DirectEdgeRequest, RuntimeEnvelope
from tangl.service.user.user import User
from tangl.story import Actor, InitMode, Player, StoryGraph, World
from tangl.story.episode import Action
from tangl.story.fabula.builder import WorldBuilder
from tangl.story.fabula.compiler import StoryCompiler
from tangl.vm import Ledger, ResolutionPhase
from tangl.vm.replay import CheckpointRecord, Patch, get_replay_engine
from tangl.vm.runtime.frame import PhaseCtx


def old_name() -> PersonalName:
    return PersonalName(given_name="Larry", family_name="Laffer", title="Mr.", gender=Gender.XY)


class NamedPlayer(PersonalNamedConcept, Player):
    """World composition, without Actor identity or a new naming authority."""


class DefaultNamedPlayer(NamedPlayer):
    """A world-specific default-created embedded value for the persistence witness."""

    personal_name: PersonalName = Field(
        default_factory=old_name,
        json_schema_extra={"include": True, "unstructurable": True},
    )


domain_dispatch = BehaviorRegistry(label="personal_name_player_test")


@domain_dispatch.register(task="story_ready")
def materialize_player(*, caller: StoryGraph, **_kwargs: object) -> None:
    player = EntityTemplate.from_data({
        "kind": DefaultNamedPlayer, "name": "Larry", "anonymous_name": "a player",
        "naming_policy": "concealed", "full_name": "Independent account name",
    }).materialize(registry=caller)
    # Mutate default-created embedded/container values in place before persistence.
    player.personal_name.nickname = "Lar"
    player.personal_name.aliases.add("L. Laffer")
    player.proper_forms.update({"familiar": "Ace", "gamer_tag": "PixelFox"})
    player.proper_aliases["The Fox"] = {"form": "gamer_tag"}


@domain_dispatch.register(task="gather_ns")
def personal_name_constructor(**_kwargs: object) -> dict[str, object]:
    # Ordinary world authority; no class/function persisted in graph.locals.
    return {"PersonalName": PersonalName}


def name_parts() -> list[dict[str, object] | str]:
    return [
        {"ref": "player", "intent": "proper"}, " / ",
        {"ref": "player", "intent": "proper", "params": {"form": "formal"}}, " / ",
        {"ref": "player", "intent": "proper", "params": {"form": "full"}},
    ]


@pytest.fixture
def world() -> Iterator[World]:
    classes = {"DefaultNamedPlayer": DefaultNamedPlayer, "ProseBlock": ProseBlock}
    bundle = StoryCompiler().compile({
        "label": "personal_name_player", "metadata": {"start_at": "s.start"},
        "scenes": {"s": {"blocks": {
            "start": {"content": "Ready.", "actions": [{
                "text": "Meet the player", "successor": "old",
                "effects": ["introduce(player)"],
            }]},
            "old": {"kind": "ProseBlock", "prose": [{"text": name_parts()}], "actions": [{
                "text": "Rename", "successor": "renamed", "effects": [
                    "player.personal_name = PersonalName(given_name='Dana', family_name='Reyes', "
                    "nickname='D', title='Mr.', gender='XY', aliases={'D. Reyes'})\n"
                    "player.name = 'Dana'",
                ],
            }]},
            "renamed": {"kind": "ProseBlock", "prose": [
                {"text": name_parts()},
                {"dialog_class": "player", "text": "Literal Larry #intro stays speech."},
            ], "actions": [{"text": "Read again", "successor": "again"}]},
            "again": {"kind": "ProseBlock", "prose": [{"text": name_parts()}]},
        }}},
    }, class_registry=classes)
    result = WorldBuilder().build(
        label="personal_name_player", bundle=bundle, class_registry=classes,
        extra_authorities=[naming_dispatch, domain_dispatch],
    )
    yield result
    World.clear_instances()


def make_ledger(world: World) -> Ledger:
    graph = world.create_story("personal_name_player", init_mode=InitMode.EAGER).graph
    return Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)


def player(ledger: Ledger) -> DefaultNamedPlayer:
    result = ledger.graph.find_one(Selector(has_kind=Player))
    assert isinstance(result, DefaultNamedPlayer)
    return result


def advance(ledger: Ledger) -> None:
    ledger.resolve_choice(next(ledger.cursor.edges_out(Selector(has_kind=Action))).uid)


def journal_dto(ledger: Ledger) -> list[dict[str, object]]:
    return RuntimeEnvelope(fragments=list(ledger.get_journal())).to_dto()["fragments"]


def test_reusable_player_forms_use_context_policy_overrides_and_per_narrator_knowledge(
    world: World,
) -> None:
    ledger = make_ledger(world)
    subject = player(ledger)
    assert isinstance(subject, PersonalNamedConcept) and isinstance(subject, Player)
    assert isinstance(subject, NamedConcept)
    assert not isinstance(subject, Actor)
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id,
                   current_phase=ResolutionPhase.JOURNAL, meta={"narrator_key": "reader"})
    operations = NamingOperations(ctx)
    assert ctx.get_ns(ctx.cursor)["player"] is subject
    familiar_override = subject.proper_forms.pop("familiar")
    assert operations.reference(subject, "proper", form="familiar") == "Lar"
    subject.proper_forms["familiar"] = familiar_override
    before = ledger.graph.value_hash()
    expected = {"familiar": "Ace", "formal": "Mr. Laffer", "full": "Larry Laffer",
                "given": "Larry", "family": "Laffer", "gamer_tag": "PixelFox"}
    for form, wording in expected.items():
        assert operations.reference(subject, "proper", form=form) == wording
    assert subject.personal_name.forms()["familiar"] == "Lar"
    assert subject.adopts()["The Fox"] == {"form": "gamer_tag"}
    assert operations.reference(subject) == "a player"
    assert subject.narrator_knowledge == {} and ledger.graph.value_hash() == before
    assert operations.introduce(subject) == "Larry"
    assert operations.reference(subject) == "Larry"
    other = ctx.derive(meta={"narrator_key": "other"})
    assert NamingOperations(other).reference(subject) == "a player"
    assert set(subject.narrator_knowledge) == {"reader"}


def test_actor_identity_defaults_and_vanilla_player_are_unchanged() -> None:
    subject = PersonalNamedActor(label="actor")
    assert type(subject) is PersonalNamedActor
    assert isinstance(subject, NamedActor) and isinstance(subject, Actor)
    assert NamedPlayer().personal_name is None
    assert subject.personal_name is None
    assert subject.get_nominal() == "actor"
    subject.name = "Display floor"
    subject.personal_name = old_name()
    assert subject.get_nominal() == "Display floor"
    assert subject.get_nominal(form="formal") == "Mr. Laffer"
    assert "personal_name" not in Player.model_fields
    assert not isinstance(Player(), NamedConcept)


def test_personal_name_assignment_does_not_implicitly_synchronize_other_names(world: World) -> None:
    ledger = make_ledger(world)
    subject = player(ledger)
    subject.personal_name = PersonalName(given_name="Dana", family_name="Reyes", gender=Gender.XY)
    operations = NamingOperations(PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id))
    assert operations.reference(subject, "proper") == "Larry"
    assert operations.reference(subject, "proper", form="given") == "Dana"
    assert subject.full_name == "Independent account name"


@pytest.mark.parametrize("after_rename", [False, True])
def test_owning_ledger_json_preserves_default_mutations_names_aliases_and_identity(
    world: World, after_rename: bool,
) -> None:
    ledger = make_ledger(world)
    advance(ledger)
    if after_rename:
        advance(ledger)
    subject = player(ledger)
    restored_graph = type(ledger.graph).structure(
        Json.deserialize(Json.serialize(ledger.graph.unstructure())),
    )
    graph_player = restored_graph.get(subject.uid)
    assert isinstance(graph_player, DefaultNamedPlayer) and not isinstance(graph_player, Actor)
    assert graph_player.personal_name.unstructure() == subject.personal_name.unstructure()
    assert restored_graph.value_hash() == ledger.graph.value_hash()
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    copy = player(restored)
    assert copy.uid == subject.uid and copy is not subject and not isinstance(copy, Actor)
    assert type(copy.personal_name) is PersonalName
    assert copy.personal_name.unstructure() == subject.personal_name.unstructure()
    assert copy.name == ("Dana" if after_rename else "Larry")
    assert copy.personal_name.nickname == ("D" if after_rename else "Lar")
    assert copy.personal_name.aliases == ({"D. Reyes"} if after_rename else {"L. Laffer"})
    assert copy.proper_forms == {"familiar": "Ace", "gamer_tag": "PixelFox"}
    assert copy.proper_aliases == {"The Fox": {"form": "gamer_tag"}}
    assert copy.peek_knowledge().state == "IDENTIFIED"
    assert journal_dto(restored) == journal_dto(ledger)


def test_actual_action_update_rename_checked_replay_and_later_realization(world: World) -> None:
    ledger = make_ledger(world)
    subject = player(ledger)
    identity = subject.uid
    advance(ledger)
    historical = journal_dto(ledger)
    old = subject.personal_name
    advance(ledger)
    assert subject.uid == identity and subject.personal_name is not old
    assert old.given_name == "Larry" and subject.personal_name.given_name == "Dana"
    assert subject.name == "Dana" and subject.full_name == "Independent account name"
    assert journal_dto(ledger)[:len(historical)] == historical
    contents = [item.content for item in ledger.get_journal() if isinstance(item, ContentFragment)]
    assert "Larry / Mr. Laffer / Larry Laffer" in contents
    assert "Dana / Mr. Reyes / Dana Reyes" in contents
    assert "Literal Larry #intro stays speech." in contents
    speech = next(item for item in ledger.get_journal() if isinstance(item, AttributedFragment))
    assert speech.who == "Dana" and speech.speaker_id == str(identity)
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    engine = get_replay_engine(restored.replay_algorithm_id)
    checkpoint = next(Selector(has_kind=CheckpointRecord).filter(restored.output_stream))
    replayed = engine.restore_checkpoint(checkpoint)
    patches = list(Selector(has_kind=Patch).filter(restored.output_stream))
    assert patches
    for patch in patches:
        replayed = engine.apply_delta(graph=replayed, delta=patch)
    replayed_player = replayed.get(identity)
    assert isinstance(replayed_player, NamedPlayer) and not isinstance(replayed_player, Actor)
    assert replayed_player.personal_name == subject.personal_name
    assert replayed_player.proper_forms == subject.proper_forms
    assert replayed_player.proper_aliases == subject.proper_aliases
    assert replayed_player.peek_knowledge().state == "IDENTIFIED"
    assert replayed.value_hash() == restored.graph.value_hash()
    history = journal_dto(restored)
    advance(restored)
    assert journal_dto(restored)[:len(history)] == history
    assert sum(item.content == "Dana / Mr. Reyes / Dana Reyes"
               for item in restored.get_journal() if isinstance(item, ContentFragment)) == 2


def test_service_json_reopen_preserves_rename_and_history_without_reset(
    world: World, tmp_path: Path,
) -> None:
    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path / "sessions")
    manager = ServiceManager(persistence)
    user = User(label="name-reader")
    persistence.save(user)
    manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    for _ in range(2):
        with manager.open_session(user_id=user.uid) as session:
            edge = next(session.ledger.cursor.edges_out(Selector(has_kind=Action)))
        manager.resolve_choice(user_id=user.uid, request=DirectEdgeRequest(edge_id=edge.uid))
    with manager.open_session(user_id=user.uid) as session:
        identity = player(session.ledger).uid
        historical = journal_dto(session.ledger)
    reopened = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "sessions"))
    # Normal live registration, not a reset or a cold bootstrap.
    assert World.get_instance(world.label) is world
    assert reopened.get_story_update(user_id=user.uid).to_dto()["fragments"] == historical
    with reopened.open_session(user_id=user.uid) as session:
        subject = player(session.ledger)
        assert subject.uid == identity and not isinstance(subject, Actor)
        assert subject.name == "Dana" and subject.personal_name.family_name == "Reyes"
        assert subject.proper_aliases["The Fox"] == {"form": "gamer_tag"}
        assert subject.peek_knowledge().state == "IDENTIFIED"
        edge = next(session.ledger.cursor.edges_out(Selector(has_kind=Action)))
    result = reopened.resolve_choice(user_id=user.uid, request=DirectEdgeRequest(edge_id=edge.uid))
    assert any(isinstance(item, ContentFragment) and item.content == "Dana / Mr. Reyes / Dana Reyes"
               for item in result.fragments)
    with reopened.open_session(user_id=user.uid) as session:
        assert journal_dto(session.ledger)[:len(historical)] == historical
