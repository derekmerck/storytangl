"""Failed figure preparation remains soft across planning and JSON restore."""
from pathlib import Path

import pytest

from tangl.core import Selector
from tangl.journal.fragments import ContentFragment, MediaFragment
from tangl.media.media_creators.svg_forge.svg_catalog import SvgCatalogDiagnostic
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager, world_registry
from tangl.service.response import DirectEdgeRequest
from tangl.story import Action


@pytest.mark.parametrize("failure", ["creator", "targets", "source", "plan"])
@pytest.mark.parametrize("reopen", [False, True])
def test_failed_figure_recovers_on_next_choice(tmp_path: Path, monkeypatch, failure: str, reopen: bool) -> None:
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [Path(__file__).resolve().parents[3] / "worlds"])
    monkeypatch.setattr("tangl.media.story_media.get_story_media_dir",
                        lambda story_id=None: tmp_path / "media" / str(story_id))
    def factory():
        return PersistenceManagerFactory.json_file(base_path=tmp_path / "store")
    service = ServiceManager(factory())
    user = service.create_user(secret="recovery").details["user_id"]
    service.create_story(user_id=user, world_id="modiste_demo")
    from modiste_demo import domain

    def choose(manager, label):
        with manager.open_session(user_id=user) as session:
            action = next(edge for edge in session.ledger.cursor.edges_out(Selector(has_kind=Action))
                          if edge.label == label)
            request = DirectEdgeRequest(edge_id=action.uid, payload=action.payload)
        return manager.resolve_choice(user_id=user, request=request)

    files_before = set((tmp_path / "media").rglob("*.svg"))
    with service.open_session(user_id=user) as session:
        resource_ids = {item.uid for item in session.ledger.graph.values() if isinstance(item, MediaRIT)}
    with monkeypatch.context() as broken:
        if failure == "creator":
            broken.setattr(domain, "palette_targets", lambda *_: (("skin", "fill", "absent", ()),))
        elif failure == "targets":
            def invalid_targets(*_):
                raise ValueError("invalid targets")
            broken.setattr(domain, "palette_targets", invalid_targets)
        elif failure == "source":
            original = ResourceManager.get_rit
            def unavailable(manager, identifier):
                return None if identifier == "afreet-subset.svg" else original(manager, identifier)
            broken.setattr(ResourceManager, "get_rit", unavailable)
        else:
            original = domain.resolve_modiste
            def invalid_plan(*args, **kwargs):
                plan = original(*args, **kwargs)
                return plan.model_copy(update={"diagnostics": (SvgCatalogDiagnostic(
                    code="invalid_test_plan", subject="fixture", detail="bad"),)})
            broken.setattr(domain, "resolve_modiste", invalid_plan)
        response = choose(service, "blue")
        assert not any(isinstance(f, MediaFragment) and f.content_format == "rit" for f in response.fragments)
        assert any(isinstance(f, ContentFragment) and isinstance(f.content, str)
                   and "Diagnostics:" in f.content for f in response.fragments)
        assert set((tmp_path / "media").rglob("*.svg")) == files_before
        with service.open_session(user_id=user) as session:
            assert {item.uid for item in session.ledger.graph.values() if isinstance(item, MediaRIT)} == resource_ids
    if reopen:
        service = ServiceManager(factory())
    response = choose(service, "blue")
    resource = next(f.content for f in response.fragments
                    if isinstance(f, MediaFragment) and f.content_format == "rit")
    assert "#B98150" in resource.path.read_text()
