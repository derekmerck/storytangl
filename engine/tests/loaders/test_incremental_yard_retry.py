"""Explicit attempt boundaries in the Salvage Yard."""
from pathlib import Path
from uuid import UUID

import pytest

from tangl.core import Selector
from tangl.mechanics.games import GamePhase, GameResult
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager, world_registry
from tangl.service.response import DirectEdgeRequest
from tangl.story import Action


@pytest.mark.parametrize("lose_first", [False, True])
def test_explicit_retry_survives_json_restore(tmp_path: Path, monkeypatch, lose_first: bool) -> None:
    worlds = Path(__file__).resolve().parents[3] / "worlds"
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [worlds])
    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path / "store")
    service = ServiceManager(persistence)
    user_id = UUID(service.create_user(secret="yard-retry").details["user_id"])
    service.create_story(user_id=user_id, world_id="incremental_yard")

    def choose(label: str) -> None:
        with service.open_session(user_id=user_id) as session:
            actions = session.ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
            action = next(a for a in actions if a.text == label or a.label == label)
            edge_id = action.uid
        service.resolve_choice(user_id=user_id, request=DirectEdgeRequest(edge_id=edge_id))

    def game(session):
        return session.ledger.graph.find_one(Selector(label="challenge")).game

    choose("Run the yard")
    with service.open_session(user_id=user_id, write_back=True) as session:
        session.ledger.graph.locals["yard_note"] = "keep"
    if lose_first:
        # Configure an actual losing cycle; the authored demo has no upkeep by default.
        with service.open_session(user_id=user_id, write_back=True) as session:
            game(session).upkeep = {"scrap": 1}
        choose("End cycle")
    else:
        for label in ("Assign 1 worker to scavenge", "End cycle", "Build signal_fire"):
            choose(label)
    with service.open_session(user_id=user_id) as session:
        assert session.ledger.cursor.label == ("defeat" if lose_first else "victory")
        assert game(session).result == (GameResult.LOSE if lose_first else GameResult.WIN)
        journal_before = [fragment.uid for fragment in session.ledger.get_journal()]

    choose("Try again" if lose_first else "Reset the yard")
    # A new service reads the persisted constructor form from JSON.
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    with service.open_session(user_id=user_id) as session:
        yard = game(session)
        assert session.ledger.cursor.label == "entrance"
        assert yard.phase == GamePhase.PENDING
        assert yard.result == GameResult.IN_PROCESS
        assert yard.history == [] and yard.round == 0
        assert yard.resources == {} and yard.worker_pool == 0
        assert yard.task_assignments == {} and yard.infrastructure == {}
        assert yard.build_counts == {} and yard.pending_rewards == {} and yard.cycle == 0
        assert yard.score == {"player": 0, "opponent": 0}
        assert yard.upkeep == ({"scrap": 1} if lose_first else {})
        assert session.ledger.graph.locals["yard_note"] == "keep"
        assert [fragment.uid for fragment in session.ledger.get_journal()][:len(journal_before)] == journal_before

    choose("Run the yard")
    for _ in range(2):
        with service.open_session(user_id=user_id) as session:
            yard = game(session)
            assert session.ledger.cursor.label == "challenge"
            assert yard.phase == GamePhase.READY and yard.resources == {"scrap": 0}
            assert yard.worker_pool == 1 and yard.task_assignments == {"scavenge": 0}
            assert yard.history == [] and yard.cycle == 0
            labels = {
                a.label for a in session.ledger.cursor.edges_out(
                    Selector(has_kind=Action, trigger_phase=None)
                )
            }
            assert "Assign 1 worker to scavenge" in labels and "End cycle" in labels
    choose("Assign 1 worker to scavenge")
    for _ in range(2):
        with service.open_session(user_id=user_id) as session:
            assert game(session).task_assignments == {"scavenge": 1}
            assert len(game(session).history) == 1
    choose("End cycle")
    if not lose_first:
        choose("Build signal_fire")
    with service.open_session(user_id=user_id) as session:
        assert session.ledger.cursor.label == ("defeat" if lose_first else "victory")
        assert game(session).result == (GameResult.LOSE if lose_first else GameResult.WIN)
