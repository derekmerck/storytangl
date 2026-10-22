"""Explicit text input is authoritative before traversal, not merely a DTO hint."""

from __future__ import annotations

import pytest

from tangl.core import BehaviorRegistry, Selector
from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.presentation.intent import (
    Accepts, BackendValidator, ComposeAccepts, EnumValidator, LengthValidator, PickAccepts,
    PiecesAccepts, PlaceAccepts, QuantityAccepts, RegexValidator, TextAccepts,
)
from tangl.service.response import DirectEdgeRequest
from tangl.story import Action, InitMode, World
from tangl.vm import Ledger
from tangl.vm.replay import CheckpointRecord, StepRecord, get_replay_engine
from tangl.vm.runtime.frame import PhaseCtx

from pytest_helpers.text_choice import text_choice_session, text_choice_world


@pytest.mark.parametrize("payload", [None, {}, {"text": None}, {"text": 123},
                                     {"text": []}, "answer"])
@pytest.mark.parametrize("required", [False, True])
def test_text_requires_explicit_string_even_when_optional(payload: object, required: bool) -> None:
    _world, manager, user, envelope = text_choice_session(TextAccepts(required=required))
    edge_id = next(f.edge_id for f in envelope.fragments if isinstance(f, ChoiceFragment))
    with manager.open_session(user_id=user.uid) as session:
        ledger_id = session.ledger.uid
        # Even a live reopened ledger must reject before any committed state
        # changes; failed Service writeback alone would not prove that.
        before = Json.serialize(session.ledger.unstructure())
        with pytest.raises(ValueError, match="text.*string|Text.*string"):
            session.ledger.resolve_choice(edge_id, choice_payload=payload)
        assert Json.serialize(session.ledger.unstructure()) == before
    stored_before = manager.persistence.storage[ledger_id]
    with pytest.raises(ValueError, match="text.*string|Text.*string"):
        manager.resolve_choice(
            user_id=user.uid, request=DirectEdgeRequest(edge_id=edge_id, payload=payload),
        )
    assert manager.persistence.storage[ledger_id] == stored_before


@pytest.mark.parametrize(("accepts", "text", "message"), [
    (TextAccepts(), "", "required"),
    (TextAccepts(), " \t\n\u00a0", "required"),
    (TextAccepts(validators=[LengthValidator(min=2, max=8)]), "x", "at least 2"),
    (TextAccepts(validators=[LengthValidator(min=2, max=8)]),
     "too long to be accepted", "at most 8"),
    (TextAccepts(required=False, validators=[LengthValidator(min=1)]), "", "at least 1"),
    (TextAccepts(validators=[RegexValidator(pattern=r"\d+", message="Need a digit")]),
     "letters", "Need a digit"),
    (TextAccepts(validators=[EnumValidator(values=["Dana"])]), " Dana ", "one of"),
    (TextAccepts(validators=[EnumValidator(values=["Dana"], case_sensitive=True)]),
     "dana", "one of"),
    (TextAccepts(validators=[EnumValidator(values=["Straße"])]), "STRASSE", "one of"),
    (TextAccepts(required=False, validators=[RegexValidator(pattern=".")]), "", "pattern"),
    (TextAccepts(required=False, validators=[EnumValidator(values=["Dana"])]), "", "one of"),
    (TextAccepts(validators=[RegexValidator(pattern="[")]), "Dana", "Invalid.*regex"),
    (TextAccepts(validators=[RegexValidator(pattern="a", flags="g")]),
     "Dana", "Unsupported.*flags"),
])
def test_rejected_constraints_leave_live_ledger_and_store_unchanged(
    accepts: TextAccepts, text: str, message: str,
) -> None:
    _world, manager, user, envelope = text_choice_session(accepts)
    edge_id = next(f.edge_id for f in envelope.fragments if isinstance(f, ChoiceFragment))
    with manager.open_session(user_id=user.uid) as session:
        ledger = session.ledger
        ledger_id = ledger.uid
        before = Json.serialize(ledger.unstructure())
        with pytest.raises(ValueError, match=message):
            ledger.resolve_choice(edge_id, choice_payload={"text": text})
        assert ledger.cursor.label == "start"
        assert ledger.graph.locals["answer"] == "untouched"
        assert ledger.graph.locals["effect_count"] == 0
        assert Json.serialize(ledger.unstructure()) == before
    stored_before = manager.persistence.storage[ledger_id]
    with pytest.raises(ValueError, match=message):
        manager.resolve_choice(
            user_id=user.uid, request=DirectEdgeRequest(edge_id=edge_id, payload={"text": text}),
        )
    assert manager.persistence.storage[ledger_id] == stored_before


@pytest.mark.parametrize(("accepts", "text"), [
    (TextAccepts(required=False), ""),
    (TextAccepts(required=False), "  \t"),
    (TextAccepts(validators=[LengthValidator(min=2, max=2)]), "😀x"),
    (TextAccepts(validators=[LengthValidator(min=3, max=3)]), " a "),
    (TextAccepts(validators=[RegexValidator(pattern=r"\d+")]), "prefix 42 suffix"),
    (TextAccepts(validators=[RegexValidator(pattern=r"^dana$", flags="im")]),
     "prefix\nDANA\nsuffix"),
    (TextAccepts(validators=[RegexValidator(pattern=r"a.b", flags="s")]), "a\nb"),
    (TextAccepts(validators=[EnumValidator(values=["Dana"])]), "dANA"),
])
def test_valid_exact_text_and_validators_survive_actual_json(
    accepts: TextAccepts, text: str,
) -> None:
    _world, manager, user, envelope = text_choice_session(accepts)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    with manager.open_session(user_id=user.uid) as session:
        restored = Ledger.structure(Json.deserialize(Json.serialize(session.ledger.unstructure())))
        assert isinstance(restored.graph.get(choice.edge_id).accepts, TextAccepts)
        restored_choice = restored.output_stream.get(choice.uid)
        assert isinstance(restored_choice.accepts, TextAccepts)
        assert restored_choice.accepts.required is accepts.required
        assert [v.unstructure() for v in restored_choice.accepts.validators] == [
            v.unstructure() for v in accepts.validators
        ]
    manager.resolve_choice(
        user_id=user.uid, request=DirectEdgeRequest(edge_id=choice.edge_id, payload={"text": text}),
    )
    with manager.open_session(user_id=user.uid) as session:
        assert isinstance(manager.persistence.storage[session.ledger.uid], str)
        assert session.ledger.cursor.label == "end"
        assert session.ledger.graph.locals["answer"] == text
        assert session.ledger.graph.locals["effect_count"] == 1
        edge = session.ledger.graph.get(choice.edge_id)
        assert isinstance(edge.accepts, TextAccepts)
        assert edge.accepts.required is accepts.required
        assert [v.unstructure() for v in edge.accepts.validators] == [
            v.unstructure() for v in accepts.validators
        ]


@pytest.mark.parametrize("override", [None, {}, {"text": "  Dana  Reyes ", "kept": 4, "extra": 9}])
def test_effect_uses_backend_merged_payload_without_changing_authored_activation(
    override: dict[str, object] | None,
) -> None:
    base = {"text": "authored", "operation": "rename", "kept": 3}
    _world, manager, user, envelope = text_choice_session(TextAccepts(), payload=base)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    manager.resolve_choice(
        user_id=user.uid, request=DirectEdgeRequest(edge_id=choice.edge_id, payload=override),
    )
    with manager.open_session(user_id=user.uid) as session:
        assert session.ledger.graph.locals["activation"] == {**base, **(override or {})}
        assert session.ledger.graph.locals["answer"] == (override or {}).get("text", base["text"])
        assert session.ledger.graph.get(choice.edge_id).payload == base


def test_unavailable_text_choice_is_still_rejected() -> None:
    _world, manager, user, envelope = text_choice_session(TextAccepts(), available=False)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    assert not choice.available
    with manager.open_session(user_id=user.uid) as session:
        before = Json.serialize(session.ledger.unstructure())
        with pytest.raises(ValueError):
            session.ledger.resolve_choice(choice.edge_id, choice_payload={"text": "Dana"})
        assert Json.serialize(session.ledger.unstructure()) == before


@pytest.mark.parametrize("accepts", [None, PickAccepts(), QuantityAccepts(), PiecesAccepts(),
                                    PlaceAccepts(), ComposeAccepts(parts=[])])
def test_other_accepts_are_not_given_text_enforcement(accepts: Accepts | None) -> None:
    _world, manager, user, envelope = text_choice_session(accepts)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    manager.resolve_choice(
        user_id=user.uid, request=DirectEdgeRequest(edge_id=choice.edge_id, payload={"text": 123}),
    )
    with manager.open_session(user_id=user.uid) as session:
        assert session.ledger.graph.locals["answer"] == 123


def test_backend_marker_leaves_domain_restrictions_to_existing_validation_path() -> None:
    world, manager, user, envelope = text_choice_session(
        TextAccepts(validators=[BackendValidator()]),
    )

    def domain_rule(*, caller: Action, ctx: PhaseCtx, **_kw: object) -> bool:
        if ctx.selected_payload["text"] == "reserved":
            raise ValueError("Name is reserved by this world")
        return True

    world.dispatch.register(domain_rule, task="validate_edge", wants_caller_kind=Action)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    with pytest.raises(ValueError, match="reserved"):
        manager.resolve_choice(
            user_id=user.uid, request=DirectEdgeRequest(edge_id=choice.edge_id,
                                                       payload={"text": "reserved"}),
        )
    manager.resolve_choice(
        user_id=user.uid,
        request=DirectEdgeRequest(edge_id=choice.edge_id, payload={"text": "Dana"}),
    )


@pytest.mark.parametrize("accepts", [None, TextAccepts()])
def test_world_false_veto_is_not_overridden_by_text_validation(
    accepts: TextAccepts | None,
) -> None:
    world, manager, user, envelope = text_choice_session(accepts)
    calls: list[str] = []

    def veto(*, caller: Action, **_kw: object) -> bool:
        calls.append(caller.text)
        return False

    world.dispatch.register(veto, task="validate_edge", wants_caller_kind=Action)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    with manager.open_session(user_id=user.uid) as session:
        before = Json.serialize(session.ledger.unstructure())
    with pytest.raises(ValueError, match="Edge validation failed"):
        manager.resolve_choice(
            user_id=user.uid,
            request=DirectEdgeRequest(edge_id=choice.edge_id, payload={"text": "Dana"}),
        )
    assert calls == ["Answer"]
    with manager.open_session(user_id=user.uid) as session:
        assert Json.serialize(session.ledger.unstructure()) == before


@pytest.mark.parametrize(("accepts", "answer"), [(None, 123), (TextAccepts(), "authored")])
def test_automatic_hops_use_authored_payload_without_a_client_text_prompt(
    accepts: TextAccepts | None, answer: str | int,
) -> None:
    _world, manager, user, _envelope = text_choice_session(
        accepts, payload={"text": answer}, activation="last",
    )
    with manager.open_session(user_id=user.uid) as session:
        assert session.ledger.cursor.label == "end"
        assert session.ledger.graph.locals["answer"] == answer
        assert session.ledger.graph.locals["effect_count"] == 1


def test_automatic_explicit_text_declaration_rejects_bad_authored_text_before_its_effect() -> None:
    world = World.from_script_data(script_data={
        "label": "automatic_text", "metadata": {"start_at": "intro.start"},
        "globals": {"effect_ran": False},
        "scenes": {"intro": {"blocks": {
            "start": {"actions": [{
                "successor": "end", "activation": "last", "accepts": {"kind": "text"},
                "payload": {"text": 123}, "effects": ["graph.locals['effect_ran'] = True"],
            }]},
            "end": {"content": "End"},
        }}},
    })
    graph = world.create_story("automatic_text").graph
    ledger = Ledger.from_graph(graph=graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    with pytest.raises(ValueError, match="string"):
        frame.goto_node(ledger.cursor)
    assert frame.cursor.label == "start"
    assert graph.locals["effect_ran"] is False


@pytest.mark.parametrize(("payload", "restore"), [
    ({"text": ""}, False),
    ({"text": 123}, False),
    ({"text": "too long to be accepted"}, False),
    ({"text": ""}, True),
])
def test_lazy_text_rejection_precedes_destination_admission_and_valid_retry(
    payload: dict[str, object], restore: bool,
) -> None:
    base = {"text": "base", "operation": "rename", "kept": 3}
    world = text_choice_world(
        TextAccepts(validators=[LengthValidator(min=2, max=8)]), payload=base,
    )
    validated: list[object] = []
    authority = BehaviorRegistry(label="lazy_text_validation")

    def validate_destination(*, caller: Action, ctx: PhaseCtx, **_kw: object) -> bool:
        assert caller.successor is not None
        validated.append(ctx.selected_payload)
        return True

    authority.register(validate_destination, task="validate_edge", wants_caller_kind=Action)
    world.extra_authorities.append(authority)
    graph = world.create_story("lazy_text", init_mode=InitMode.LAZY).graph
    ledger = Ledger.from_graph(graph=graph, entry_id=graph.initial_cursor_id)
    if restore:
        ledger = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
        graph = ledger.graph
    edge = graph.find_one(Selector(has_kind=Action))
    assert edge.successor_id is None
    members = set(graph.members)
    history = list(ledger.cursor_history)
    before = Json.serialize(ledger.unstructure())

    with pytest.raises(ValueError):
        ledger.resolve_choice(edge.uid, choice_payload=payload)

    assert set(graph.members) == members
    assert edge.successor_id is None
    assert ledger.cursor.label == "start"
    assert ledger.cursor_history == history
    assert graph.locals["answer"] == "untouched"
    assert graph.locals["effect_count"] == 0
    assert Json.serialize(ledger.unstructure()) == before
    assert validated == []

    # Retry on this very ledger, not a fresh/eager graph or discarded Service load.
    override = {"text": "  Dana ", "kept": 4}
    ledger.resolve_choice(edge.uid, choice_payload=override)
    assert len(graph) == len(members) + 1
    assert edge.successor is ledger.cursor and ledger.cursor.label == "end"
    assert ledger.cursor_history == [*history, ledger.cursor.uid]
    assert ledger.choice_steps == 1
    assert graph.locals["effect_count"] == 1
    assert graph.locals["answer"] == override["text"]
    assert graph.locals["activation"] == {**base, **override}
    assert edge.payload == base
    assert validated == [{**base, **override}]
    assert len([
        f for f in ledger.output_stream.values()
        if isinstance(f, ContentFragment) and f.content == "Answer saved."
    ]) == 1

    # Replay the admitted destination/binding from the pre-hop checkpoint;
    # replay must not run validation or effects or append journal output again.
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    checkpoint = restored.output_stream.find_one(Selector(has_kind=CheckpointRecord))
    step = restored.output_stream.find_one(Selector(has_kind=StepRecord))
    engine = get_replay_engine(restored.replay_algorithm_id)
    replay_graph = engine.restore_checkpoint(checkpoint)
    assert replay_graph.get(edge.uid).successor is None
    replay_graph = engine.apply_delta(
        graph=replay_graph, delta=restored.output_stream.get(step.delta_id),
    )
    replay_edge = replay_graph.get(edge.uid)
    assert replay_edge.successor.uid == ledger.cursor.uid
    assert replay_graph.locals["effect_count"] == 1
    assert validated == [{**base, **override}]
    assert len([
        f for f in restored.output_stream.values()
        if isinstance(f, ContentFragment) and f.content == "Answer saved."
    ]) == 1
