"""Fresh-process restoration of Grand Grotto's graph-owned asset tokens."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID

from tangl.core import Selector
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager, world_registry
from tangl.service.response import DirectEdgeRequest
from tangl.story import Action
from tangl.vm.replay import CheckpointRecord


def _process(root: Path, mode: str) -> None:
    # Configure these before importing the service or its settings.
    os.environ["TANGL_SERVICE__PATHS__CACHE_DATA"] = f"@path {root / 'cache'}"
    os.environ["TANGL_SERVICE__PATHS__STORY_MEDIA"] = f"@path {root / 'media'}"
    from tangl.core import Selector, Token
    from tangl.loaders.compilers import AssetCompiler
    from tangl.mechanics.sandbox import SandboxCompiledAssetType
    from tangl.persistence import PersistenceManagerFactory
    from tangl.service import ServiceManager, world_registry
    from tangl.story import Action

    worlds = Path(__file__).resolve().parents[3] / "worlds"
    world_registry.get_world_dirs = lambda: [worlds]
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=root / "store"))

    if mode == "write":
        user = UUID(service.create_user(secret="catalog-writer").details["user_id"])
        service.create_story(user_id=user, world_id="adventure_sandbox_slice")
        with service.open_session(user_id=user, write_back=True) as session:
            ledger = session.ledger
            enter = next(a for a in ledger.cursor.edges_out() if isinstance(a, Action)
                         and a.text == "Stand at the end of the road")
            ledger.resolve_choice(enter.uid)
            tokens = list(ledger.graph.find_all(Selector(has_kind=Token[SandboxCompiledAssetType])))
            lamp = next(token for token in tokens if token.label == "brass_lamp")
            # Holder custody is a separate known persistence gap, so exercise the
            # graph-owned token directly rather than reseeding its inventory.
            lamp.lit = True
            lamp.charge.current = 321
            receipt = {
                "user": str(user),
                "tokens": {token.label: str(token.uid) for token in tokens},
                "charge": lamp.charge.current,
            }
        (root / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    else:
        # Another catalog may use the same short authored handle before world loading.
        competing = root / "competing.yaml"
        competing.write_text("brass_lamp:\n  name: other lamp\n", encoding="utf-8")
        other = AssetCompiler._load_catalog(source_path=competing,
                    definition_type=SandboxCompiledAssetType, world_label="other_world",
                    catalog_label="adventure")
        other_lamp = next(other.find_all(Selector(catalog_id="brass_lamp")))
        receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
        assert (Token, SandboxCompiledAssetType) not in Token._wrapper_cache
        with service.open_session(user_id=UUID(receipt["user"])) as session:
            tokens = list(session.ledger.graph.find_all(
                Selector(has_kind=Token[SandboxCompiledAssetType])
            ))
            assert len(tokens) == len(receipt["tokens"]) == 4
            assert {token.label: str(token.uid) for token in tokens} == receipt["tokens"]
            lamp = next(token for token in tokens if token.label == "brass_lamp")
            assert lamp.reference_singleton is not other_lamp
            assert lamp.reference_singleton is SandboxCompiledAssetType.get_instance(
                "adventure_sandbox_slice:adventure:brass_lamp")
            assert lamp.name == "brass lantern" and lamp.lit
            assert lamp.charge.current == receipt["charge"]


def test_cold_service_restores_catalog_tokens(tmp_path: Path) -> None:
    for mode in ("write", "read"):
        subprocess.run([sys.executable, __file__, mode, str(tmp_path)], check=True,
                       env=os.environ.copy(), timeout=60)


def test_saved_grotto_checkpoint_survives_restore_and_rollback(tmp_path: Path, monkeypatch) -> None:
    worlds = Path(__file__).resolve().parents[3] / "worlds"
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [worlds])
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    user = UUID(service.create_user(secret="checkpoint-reader").details["user_id"])
    service.create_story(user_id=user, world_id="adventure_sandbox_slice")
    for label in ("Stand at the end of the road", "Go east to Inside Building",
                  "Go west to End of Road"):
        with service.open_session(user_id=user) as session:
            edge = next(a for a in session.ledger.cursor.edges_out(Selector(has_kind=Action))
                        if a.text == label)
            request = DirectEdgeRequest(edge_id=edge.uid, payload=edge.payload)
        service.resolve_choice(user_id=user, request=request)
    with service.open_session(user_id=user) as session:
        ledger = session.ledger
        checkpoints = list(Selector(has_kind=CheckpointRecord).filter(ledger.output_stream))
        assert all(c.restore_graph().value_hash() == c.state_hash for c in checkpoints)
        ledger.rollback_to_step(ledger.cursor_steps - 1)
        assert ledger.cursor.label == "building"


if __name__ == "__main__":
    _process(Path(sys.argv[2]), sys.argv[1])
