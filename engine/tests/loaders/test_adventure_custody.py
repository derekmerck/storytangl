"""Grand Grotto custody and shared fixture identity across cold Service restore."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID


def _run(root: Path, mode: str) -> None:
    os.environ["TANGL_SERVICE__PATHS__CACHE_DATA"] = f"@path {root / 'cache'}"
    os.environ["TANGL_SERVICE__PATHS__STORY_MEDIA"] = f"@path {root / 'media'}"
    from tangl.core import Selector, Token
    from tangl.persistence import PersistenceManagerFactory
    from tangl.service import ServiceManager, world_registry
    from tangl.service.response import DirectEdgeRequest
    from tangl.story import Action
    from tangl.mechanics.sandbox.handlers import _visibility_ns
    from tangl.vm.runtime.frame import PhaseCtx
    from tangl.vm.replay import CheckpointRecord

    world_registry.get_world_dirs = lambda: [Path(__file__).resolve().parents[3] / "worlds"]
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=root / "store"))
    if mode == "write":
        user = UUID(service.create_user(secret="grotto-custody").details["user_id"])
        service.create_story(user_id=user, world_id="adventure_sandbox_slice")
        with service.open_session(user_id=user, write_back=True) as session:
            session.ledger.checkpoint_cadence = 100
    else:
        receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
        user = UUID(receipt["user"])

    def choose(text=None, **hints):
        with service.open_session(user_id=user) as session:
            choices = session.ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
            edge = next(a for a in choices if (text is None or a.text == text) and
                        all(a.ui_hints.model_dump().get(key) == value for key, value in hints.items()))
            request = DirectEdgeRequest(edge_id=edge.uid, payload=edge.payload)
        service.resolve_choice(user_id=user, request=request)

    if mode == "write":
        choose(text="Stand at the end of the road")
        choose(contribution="movement", direction="east")
        choose(contribution="take", asset="keys")
        choose(contribution="take", asset="brass_lamp")
        choose(contribution="light", asset="brass_lamp", verb="turn_on")
        choose(contribution="movement", direction="west")
        for _ in range(3):
            choose(contribution="movement", direction="south")
        choose(contribution="unlock", target="grate")
        choose(contribution="open", target="grate")
        with service.open_session(user_id=user) as session:
            graph = session.ledger.graph
            scope = graph.find_one(Selector(label="cave"))
            outside = graph.find_one(Selector(label="outside_grate"))
            below = graph.find_one(Selector(label="below_grate"))
            grate = outside.fixture_by_label("grate")
            lamp = scope.player_assets.get_asset("brass_lamp")
            keys = scope.player_assets.get_asset("keys")
            assert below.fixture_by_label("grate") is grate
            assert grate.open and not grate.locked and lamp.lit
            receipt = {"user": str(user), "grate": str(grate.uid), "lamp": str(lamp.uid),
                       "keys": str(keys.uid), "player_wallet": str(scope.player_assets.discrete_wallet_id),
                       "building_wallet": str(graph.find_one(Selector(label="building")).discrete_wallet_id),
                       "tokens": sorted(str(item.uid) for item in graph.find_all(Selector(has_kind=Token))),
                       "charge": lamp.charge.current}
        (root / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        return

    with service.open_session(user_id=user) as session:
        graph = session.ledger.graph
        outside = graph.find_one(Selector(label="outside_grate"))
        below = graph.find_one(Selector(label="below_grate"))
        grate = outside.fixture_by_label("grate")
        scope = graph.find_one(Selector(label="cave"))
        lamp = scope.player_assets.get_asset("brass_lamp")
        assert below.fixture_by_label("grate") is grate is graph.get(UUID(receipt["grate"]))
        assert len(list(graph.find_all(Selector(label="grate")))) == 1
        assert grate.open and not grate.locked
        assert lamp is graph.get(UUID(receipt["lamp"])) and lamp.lit
        assert lamp.charge.current == receipt["charge"]
        assert scope.player_assets.discrete_wallet_id == UUID(receipt["player_wallet"])
        building = graph.find_one(Selector(label="building"))
        assert building.discrete_wallet_id == UUID(receipt["building_wallet"])
        assert sorted(str(item.uid) for item in graph.find_all(Selector(has_kind=Token))) == receipt["tokens"]
        before = graph.value_hash(), len(graph.members)
        assert scope.player_assets.get_asset("keys") is graph.get(UUID(receipt["keys"]))
        assert (graph.value_hash(), len(graph.members)) == before
    choose(contribution="movement", direction="down")
    with service.open_session(user_id=user) as session:
        graph = session.ledger.graph
        below = session.ledger.cursor
        assert below.label == "below_grate"
        ctx = PhaseCtx(graph=graph, cursor_id=below.uid)
        assert _visibility_ns(below, ctx)["sandbox_has_lit_light_source"]()
        assert below.fixture_by_label("grate") is graph.get(UUID(receipt["grate"]))
    choose(contribution="light", asset="brass_lamp", verb="turn_off")
    with service.open_session(user_id=user) as session:
        ctx = PhaseCtx(graph=session.ledger.graph, cursor_id=session.ledger.cursor_id)
        assert not _visibility_ns(session.ledger.cursor, ctx)["sandbox_has_lit_light_source"]()
    choose(contribution="light", asset="brass_lamp", verb="turn_on")
    choose(contribution="movement", direction="up")
    with service.open_session(user_id=user) as session:
        assert session.ledger.cursor.label == "outside_grate"
        assert session.ledger.cursor.fixture_by_label("grate").open
    choose(contribution="drop", asset="brass_lamp")
    with service.open_session(user_id=user) as session:
        graph = session.ledger.graph
        room = session.ledger.cursor
        ctx = PhaseCtx(graph=graph, cursor_id=room.uid)
        assert not _visibility_ns(room, ctx)["sandbox_has_lit_light_source"]()
        assert room.get_asset("brass_lamp") is graph.get(UUID(receipt["lamp"]))
    choose(contribution="take", asset="brass_lamp")
    choose(contribution="movement", direction="down")
    choose(contribution="movement", direction="west")
    choose(contribution="take", asset="wicker_cage")
    choose(contribution="put", asset="keys", target="wicker_cage")
    with service.open_session(user_id=user) as session:
        graph = session.ledger.graph
        scope = graph.find_one(Selector(label="cave"))
        cage = scope.player_assets.get_asset("wicker_cage")
        assert cage.container.get_asset("keys") is graph.get(UUID(receipt["keys"]))
        cage_uid, wallet_uid = cage.uid, cage.container.discrete_wallet_id
        assert not scope.player_assets.has_asset("keys")
    choose(contribution="take_from_container", asset="keys", target="wicker_cage")
    with service.open_session(user_id=user, write_back=True) as session:
        graph = session.ledger.graph
        scope = graph.find_one(Selector(label="cave"))
        assert scope.player_assets.get_asset("keys") is graph.get(UUID(receipt["keys"]))
        cage = scope.player_assets.get_asset("wicker_cage")
        assert cage.uid == cage_uid and cage.container.discrete_wallet_id == wallet_uid
        assert not cage.container.assets
        target = session.ledger.cursor_steps - 1
        checkpoints = Selector(has_kind=CheckpointRecord).filter(session.ledger.output_stream)
        assert max(c.step for c in checkpoints if c.step <= target) < target
        session.ledger.rollback_to_step(target)
        graph = session.ledger.graph
        scope = graph.find_one(Selector(label="cave"))
        cage = scope.player_assets.get_asset("wicker_cage")
        assert cage.container.get_asset("keys") is graph.get(UUID(receipt["keys"]))
        assert not scope.player_assets.has_asset("keys")
    with service.open_session(user_id=user) as session:
        graph = session.ledger.graph
        scope = graph.find_one(Selector(label="cave"))
        cage = scope.player_assets.get_asset("wicker_cage")
        assert cage.container.get_asset("keys") is graph.get(UUID(receipt["keys"]))


def test_cold_service_custody_and_shared_grate(tmp_path: Path) -> None:
    for mode in ("write", "read"):
        subprocess.run([sys.executable, __file__, mode, str(tmp_path)],
                       check=True, env=os.environ.copy(), timeout=60)


if __name__ == "__main__":
    _run(Path(sys.argv[2]), sys.argv[1])
