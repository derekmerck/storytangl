"""Interactive catalogue choices survive JSON-backed Service reopen."""
from pathlib import Path
import re

from tangl.core import Selector
from tangl.journal.fragments import ContentFragment
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager, world_registry
from tangl.service.response import DirectEdgeRequest
from tangl.story import Action


def test_modiste_choices_restore_and_continue(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [Path(__file__).resolve().parents[3] / "worlds"])
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    user = service.create_user(secret="modiste").details["user_id"]
    service.create_story(user_id=user, world_id="modiste_demo")
    from modiste_demo import domain
    calls = []
    original_load = domain.load_pack

    def count_load(manager):
        calls.append(manager)
        return original_load(manager)

    monkeypatch.setattr(domain, "load_pack", count_load)

    def choose(manager: ServiceManager, label: str):
        with manager.open_session(user_id=user) as session:
            action = next(edge for edge in session.ledger.cursor.edges_out(Selector(has_kind=Action))
                          if edge.label == label)
            request = DirectEdgeRequest(edge_id=action.uid, payload=action.payload)
        return manager.resolve_choice(user_id=user, request=request)

    choose(service, "camisole")
    response = choose(service, "blue")
    text = " ".join(f.content for f in response.fragments if isinstance(f, ContentFragment))
    assert "Outfit: camisole" in text and "Palette: blue" in text
    assert "top.camisole" in text and "feet.slippers" in text
    identity = re.search(r"Plan: ([a-f0-9]{64})", text).group(1)
    reopened = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    with reopened.open_session(user_id=user) as session:
        assert session.ledger.cursor.outfit == "camisole" and session.ledger.cursor.palette == "blue"
        before = session.ledger.graph.value_hash(), len(session.ledger.graph.members)
    update = reopened.get_story_update(user_id=user)
    text = " ".join(f.content for f in update.fragments if isinstance(f, ContentFragment))
    assert f"Plan: {identity}" in text
    with reopened.open_session(user_id=user) as session:
        assert (session.ledger.graph.value_hash(), len(session.ledger.graph.members)) == before
    response = choose(reopened, "blue")
    text = " ".join(f.content for f in response.fragments if isinstance(f, ContentFragment))
    assert f"Plan: {identity}" in text
    assert "Outfit: camisole" in text and "Palette: blue" in text
    assert calls == []
