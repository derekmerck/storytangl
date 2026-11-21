"""Shipped Crossroads bundles through discovery, Service and JSON persistence."""
from pathlib import Path
import shutil
from uuid import UUID

import pytest
import yaml

from tangl.core import Selector
from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.persistence import PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.service import ServiceManager, world_registry
from tangl.service.response import DirectEdgeRequest
from tangl.story import Action, Actor, Scene, World
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision


WORLDS = Path(__file__).resolve().parents[3] / "worlds"
TALK = "Ask Aria about the northern road"


def _choices(envelope):
    return {fragment.text: fragment for fragment in envelope.fragments
            if isinstance(fragment, ChoiceFragment)}


@pytest.mark.parametrize("variant", ["receiver", "sponsor"])
@pytest.mark.parametrize("caller", ["hearth", "table"])
def test_shipped_crossroads_service_json(variant, caller, tmp_path, monkeypatch):
    registry = world_registry.WorldRegistry(world_dirs=[WORLDS])
    assert {"crossroads_receiver", "crossroads_sponsor"} <= registry.openable.keys()
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [WORLDS])
    world_registry.clear_discovered_world_registries()
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    user = UUID(service.create_user(secret=f"{variant}-{caller}").details["user_id"])
    world_id = f"crossroads_{variant}"
    envelope = service.create_story(user_id=user, world_id=world_id)
    assert not _choices(envelope)["Leave with the news"].available

    def choose(text):
        nonlocal envelope
        choice = _choices(envelope)[text]
        assert choice.available
        envelope = service.resolve_choice(user_id=user, request=DirectEdgeRequest(edge_id=choice.edge_id))

    if caller == "table":
        choose("Walk to the table")
    with service.open_session(user_id=user) as session:
        assert session.ledger.cursor.label == caller
        scene = session.ledger.graph.find_one(Selector(has_kind=Scene, label="aria.conversation"))
        aria = session.ledger.graph.find_one(Selector(has_kind=Actor, label="aria"))
        assert scene.owner is aria
        scene_id, aria_id = scene.uid, aria.uid
    choose(TALK)
    assert any("northern road is open again" in fragment.content for fragment in envelope.fragments
               if isinstance(fragment, ContentFragment))
    with service.open_session(user_id=user) as session:
        ledger = session.ledger
        assert ledger.cursor.label == caller
        assert ledger.graph.locals["rumors_heard"] == 1
        assert scene_id in ledger.cursor_history
        assert ledger.graph.get(scene_id).owner is ledger.graph.get(aria_id)
        assert len(list(ledger.graph.find_all(Selector(has_kind=Scene, label="aria.conversation")))) == 1
        restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
        restored_scene = restored.graph.get(scene_id)
        assert restored_scene.owner is restored.graph.get(aria_id)
        before = [edge.uid for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                  if edge.successor_id == scene_id]
        do_provision(restored.cursor, ctx=restored.get_frame()._make_ctx())
        after = [edge.uid for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                 if edge.successor_id == scene_id]
        assert before == after and len(after) == 1
        nav_text = "Walk to the table" if caller == "hearth" else "Return to the hearth"
        nav = next(edge for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                   if edge.text == nav_text)
        restored.resolve_choice(nav.uid)
        assert restored.cursor.label == ("table" if caller == "hearth" else "hearth")
        (other_call,) = [edge for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                         if edge.successor_id == scene_id]
        assert not other_call.available(ctx=restored.get_frame()._make_ctx())
    assert not _choices(envelope)[TALK].available
    assert _choices(envelope)["Leave with the news"].available
    choose("Walk to the table" if caller == "hearth" else "Return to the hearth")
    assert not _choices(envelope)[TALK].available
    choose("Step outside")
    with service.open_session(user_id=user) as session:
        ledger = session.ledger
        assert ledger.cursor.label == "yard"
        calls = [edge for edge in ledger.cursor.edges_out(Selector(has_kind=Action))
                 if edge.successor_id == scene_id]
        assert len(calls) == (1 if variant == "receiver" else 0)
        assert ledger.graph.get(scene_id).owner is ledger.graph.get(aria_id)
    if variant == "receiver":
        assert not _choices(envelope)[TALK].available
    else:
        assert TALK not in _choices(envelope)


@pytest.mark.parametrize("variant", ["receiver", "sponsor"])
def test_outside_control_before_conversation(variant, tmp_path, monkeypatch):
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [WORLDS])
    world_registry.clear_discovered_world_registries()
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    user = UUID(service.create_user(secret=f"outside-{variant}").details["user_id"])
    envelope = service.create_story(user_id=user, world_id=f"crossroads_{variant}")
    edge_id = _choices(envelope)["Step outside"].edge_id
    envelope = service.resolve_choice(user_id=user, request=DirectEdgeRequest(edge_id=edge_id))
    with service.open_session(user_id=user) as session:
        graph = session.ledger.graph
        scene = graph.find_one(Selector(has_kind=Scene, label="aria.conversation"))
        assert graph.find_one(Selector(has_kind=Actor, label="aria")) is scene.owner
        calls = [edge for edge in session.ledger.cursor.edges_out(Selector(has_kind=Action))
                 if edge.successor_id == scene.uid]
        assert len(calls) == (1 if variant == "receiver" else 0)
    if variant == "receiver":
        assert not _choices(envelope)[TALK].available
    else:
        assert TALK not in _choices(envelope)


def test_shipped_variants_have_the_same_service_journey(tmp_path, monkeypatch):
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [WORLDS])
    world_registry.clear_discovered_world_registries()
    journeys = []
    for variant in ("receiver", "sponsor"):
        service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / variant))
        user = UUID(service.create_user(secret=f"compare-{variant}").details["user_id"])
        envelope = service.create_story(user_id=user, world_id=f"crossroads_{variant}")
        snapshots = []
        for choice_text in (TALK, "Walk to the table", "Step outside"):
            snapshots.append((
                [fragment.content for fragment in envelope.fragments
                 if isinstance(fragment, ContentFragment)],
                {text for text, choice in _choices(envelope).items() if choice.available},
            ))
            envelope = service.resolve_choice(
                user_id=user, request=DirectEdgeRequest(edge_id=_choices(envelope)[choice_text].edge_id),
            )
        snapshots.append((
            [fragment.content for fragment in envelope.fragments if isinstance(fragment, ContentFragment)],
            {text for text, choice in _choices(envelope).items() if choice.available},
        ))
        journeys.append(snapshots)
    assert journeys[0] == journeys[1]


def test_aria_busy_extension_keeps_offer_identity_and_once(tmp_path, monkeypatch):
    bundle = tmp_path / "worlds" / "crossroads_sponsor"
    shutil.copytree(WORLDS / "crossroads_sponsor", bundle)
    script_path = bundle / "script.yaml"
    script = yaml.safe_load(script_path.read_text())
    script["globals"]["aria_ready"] = False
    script["actors"]["aria"]["episodes"]["conversation"]["offer"]["availability"] = [
        {"expr": "aria_ready"},
    ]
    script["scenes"]["inn"]["blocks"]["hearth"]["actions"].append({
        "text": "Wait for Aria", "successor": "hearth",
        "effects": ["graph.locals['aria_ready'] = True"],
    })
    script_path.write_text(yaml.safe_dump(script, sort_keys=False))
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [bundle.parent])
    world_registry.clear_discovered_world_registries()
    World.clear_instances()
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    user = UUID(service.create_user(secret="aria-busy").details["user_id"])
    envelope = service.create_story(user_id=user, world_id="crossroads_sponsor")
    initial = _choices(envelope)[TALK]
    assert not initial.available
    envelope = service.resolve_choice(
        user_id=user, request=DirectEdgeRequest(edge_id=_choices(envelope)["Wait for Aria"].edge_id),
    )
    ready = _choices(envelope)[TALK]
    assert ready.available and ready.edge_id == initial.edge_id
    envelope = service.resolve_choice(user_id=user, request=DirectEdgeRequest(edge_id=ready.edge_id))
    assert any("northern road is open again" in f.content for f in envelope.fragments
               if isinstance(f, ContentFragment))
    assert not _choices(envelope)[TALK].available
    assert _choices(envelope)[TALK].edge_id == initial.edge_id
    with service.open_session(user_id=user) as session:
        assert session.ledger.cursor.label == "hearth"
        assert session.ledger.graph.locals["aria_ready"] is True


def _call(owner):
    return {"successor": f"{owner}.conversation", "return": True, "once": True,
            "conditions": [f"'{owner}' in roles"]}


def _add_bram(script, variant):
    script["actors"]["bram"] = {"name": "Bram", "episodes": {"conversation": {
        "action_name": "Ask Bram about the bridge",
        "blocks": {"message": {"content": "Bram says the bridge is sound."}},
    }}}
    episode = script["actors"]["bram"]["episodes"]["conversation"]
    if variant == "sponsor":
        episode["offer"] = {"source_requirement": {"has_tags": ["crossroads_inn"]}, "once": True}
    script["scenes"]["inn"]["roles"]["bram"] = {"actor_ref": "bram"}
    if variant == "receiver":
        blocks = script["scenes"]["inn"]["blocks"]
        blocks["hearth"]["actions"].append(_call("bram"))
        blocks["table"]["actions"].append(_call("bram"))
        script["scenes"]["outside"]["blocks"]["yard"]["actions"].append(_call("bram"))
        if "porch" in blocks:
            blocks["porch"]["actions"].append(_call("bram"))


def _add_porch(script, variant):
    blocks = script["scenes"]["inn"]["blocks"]
    blocks["hearth"]["actions"].append({"text": "Walk to the porch", "successor": "porch"})
    blocks["porch"] = {"content": "The porch is sheltered from the rain.", "actions": [
        {"text": "Return to the hearth", "successor": "hearth"},
    ]}
    if variant == "receiver":
        aria_call = _call("bard")
        aria_call["successor"] = "aria.conversation"
        blocks["porch"]["actions"].append(aria_call)
        if "bram" in script["actors"]:
            blocks["porch"]["actions"].append(_call("bram"))


@pytest.mark.parametrize("variant", ["receiver", "sponsor"])
@pytest.mark.parametrize("order", [("bram", "porch"), ("porch", "bram")])
def test_authored_extensions_compose_in_either_order(variant, order, tmp_path, monkeypatch):
    world_id = f"crossroads_{variant}"
    bundle = tmp_path / "worlds" / world_id
    shutil.copytree(WORLDS / world_id, bundle)
    script_path = bundle / "script.yaml"
    script = yaml.safe_load(script_path.read_text())
    for addition in order:
        if addition == "bram":
            _add_bram(script, variant)
        else:
            _add_porch(script, variant)
    script_path.write_text(yaml.safe_dump(script, sort_keys=False))
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [bundle.parent])
    world_registry.clear_discovered_world_registries()
    World.clear_instances()
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    user = UUID(service.create_user(secret=f"{variant}-{order}").details["user_id"])
    envelope = service.create_story(user_id=user, world_id=world_id)
    for move in ("Walk to the table", "Return to the hearth", "Walk to the porch"):
        choices = _choices(envelope)
        assert choices[TALK].available
        assert choices["Ask Bram about the bridge"].available
        envelope = service.resolve_choice(
            user_id=user, request=DirectEdgeRequest(edge_id=choices[move].edge_id),
        )
    assert _choices(envelope)[TALK].available
    assert _choices(envelope)["Ask Bram about the bridge"].available
    envelope = service.resolve_choice(
        user_id=user,
        request=DirectEdgeRequest(edge_id=_choices(envelope)["Ask Bram about the bridge"].edge_id),
    )
    assert any("bridge is sound" in fragment.content for fragment in envelope.fragments
               if isinstance(fragment, ContentFragment))
    assert _choices(envelope)[TALK].available
    assert not _choices(envelope)["Ask Bram about the bridge"].available
    with service.open_session(user_id=user) as session:
        assert session.ledger.cursor.label == "porch"
