"""Tests for the credential gate demo world bundle."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.credentials import (
    CredentialDefinition,
    CredentialStatus,
    CredentialToken,
    Restrictions,
    RestrictionLevel,
    materialize_packet,
)
from tangl.mechanics.games.credentials_game import (
    CredentialCase,
    CredentialPresentationProfile,
    CredentialsGame,
    CredentialsGameHandler,
    Finding,
)
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _credential_gate_root() -> Path:
    return _repo_worlds_dir() / "credential_gate"


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


def _choose(ledger: Ledger, label: str) -> None:
    # Story-authored actions surface their display string as ``text`` (a typed
    # ``str``, defaults to ``""``); game-provisioned actions surface it as
    # ``label`` (from get_move_label). Both fields are declared, so equality
    # checks are safe even when one side is the unused default.
    action = next(
        a for a in _actions(ledger) if a.label == label or a.text == label
    )
    ledger.resolve_choice(action.uid)


def _inspect(ledger: Ledger, target: str) -> None:
    action = next(a for a in _actions(ledger) if a.label == "Inspect a document")
    game = ledger.cursor.game
    ledger.resolve_choice(
        action.uid,
        choice_payload={"piece_ids": [f"{game.case_index}:{target}"]},
    )


class TestCredentialGateWorld:
    """Tests for the staged credentials demo world."""

    def test_world_registry_discovers_credential_gate(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "credential_gate" in registry.bundles
        bundle = registry.bundles["credential_gate"]
        assert bundle.manifest.label == "credential_gate"
        assert bundle.manifest.metadata["title"] == "Credential Gate"

    def test_compiles_qualified_credential_catalog_idempotently(self) -> None:
        bundle = WorldBundle.load(_credential_gate_root())
        compiler = WorldCompiler()
        first = compiler.compile(bundle)
        compiler.asset_compiler.load_into(bundle, first.assets, first.class_registry)

        definitions = first.assets.values["CredentialDefinition"]

        assert CredentialDefinition.get_instance("credential_gate:work_permit") in definitions
        assert {
            definition.catalog_id for definition in definitions
        } >= {"work_permit", "passport_work"}

    def test_compiled_hall_monitor_uses_authored_ids_and_wording(self, tmp_path: Path) -> None:
        root = tmp_path / "hall_monitor"
        package = root / "hall_monitor"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "domain.py").write_text(
            "from tangl.mechanics.credentials import CredentialDefinition\n",
            encoding="utf-8",
        )
        (root / "world.yaml").write_text(
            """label: hall_monitor
scripts: script.yaml
domain_module: hall_monitor.domain
assets:
  - asset_kind: CredentialDefinition
    source: credential_types.yaml
""",
            encoding="utf-8",
        )
        (root / "script.yaml").write_text(
            """label: hall_monitor
metadata:
  title: Hall Monitor
scenes:
  hall:
    blocks:
      entrance:
        content: A student approaches.
""",
            encoding="utf-8",
        )
        (root / "credential_types.yaml").write_text(
            """student_id:
  name: Student ID
  origin_ids: [lower_school]
  indication: activity
  document_kind: id
  requires_id: false
activity_pass:
  name: Activity Pass
  origin_ids: [lower_school]
  indication: activity
  document_kind: document
  requires_id: true
  facets:
    - channel: choice
      facet_type: giver
      payload: request_document
""",
            encoding="utf-8",
        )
        world = WorldCompiler().compile(WorldBundle.load(root))
        manager = materialize_packet(
            owner=object(),
            region="lower_school",
            purpose="activity",
            id_card=CredentialToken(indication="activity"),
            credentials=[
                CredentialToken(
                    indication="activity",
                    status=CredentialStatus.MISSING_SEAL,
                    requires_id=True,
                )
            ],
            possessions=[],
            label_prefix="Nia",
            catalog_namespace="hall_monitor",
        )
        game = CredentialsGame(
            roster=[CredentialCase(packet_manager=manager)],
            restriction_map=Restrictions.from_map(
                {"lower_school": {"activity": RestrictionLevel.WITH_PERMIT}}
            ),
            catalog_namespace="hall_monitor",
            presentation=CredentialPresentationProfile(
                move_labels={"request_document": "Ask for corrected {document}"},
                journal_text={
                    "request_document": "You ask for a corrected {document}.",
                    "request_document_cleared": "A signed replacement pass is produced.",
                    "request_document_not_applicable": "No pass can be produced.",
                },
            ),
        )
        handler = CredentialsGameHandler()
        handler.setup(game)
        handler.receive_move(game, ("inspect", "passport"))
        move = next(move for move in handler.get_available_moves(game) if move.kind == "request_document")

        assert world.assets.values["CredentialDefinition"][1].catalog_namespace == "hall_monitor"
        assert move.target == "activity"
        assert handler.get_move_label(game, move) == "Ask for corrected Activity Pass"

        handler.receive_move(game, ("request_document", "activity"))

        assert game.finding_status == {"activity": Finding.CLEARED}
        assert "A signed replacement pass is produced." in [
            fragment.content for fragment in handler.get_journal_fragments(game)
        ]

    def test_scheduled_shift_routes_to_victory(self) -> None:
        bundle = WorldBundle.load(_credential_gate_root())
        world = WorldCompiler().compile(bundle)

        assert "CredentialGateBlock" in world.class_registry

        result = world.create_story("credential_gate_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"
        _choose(ledger, "Work the scheduled shift")
        assert ledger.cursor.label == "standard_challenge"

        # The authored roster: Tomas (pass), Edda (deny), Goran (arrest).
        _inspect(ledger, "passport")
        _choose(ledger, "Choose pass")
        assert ledger.cursor.label == "standard_challenge"  # still mid-shift

        _inspect(ledger, "passport")
        _choose(ledger, "Choose deny")
        assert ledger.cursor.label == "standard_challenge"

        _inspect(ledger, "passport")
        _choose(ledger, "Choose arrest")

        assert ledger.cursor.label == "victory"
        content = " ".join(
            f.content
            for f in ledger.get_journal()
            if isinstance(f.content, str)
        )
        assert "shift complete" in content.lower()

    def test_randomized_shift_materializes_lazily_and_routes_to_victory(self) -> None:
        """The sampled path materializes each candidate on arrival and, played
        correctly, routes to the same victory ending."""

        bundle = WorldBundle.load(_credential_gate_root())
        world = WorldCompiler().compile(bundle)

        assert "SampledGateBlock" in world.class_registry

        result = world.create_story("credential_gate_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        _choose(ledger, "Work a randomized shift")
        assert ledger.cursor.label == "sampled_challenge"

        game = ledger.cursor.game
        total = game._total_cases()
        assert total > 1
        # Lazy: only the active arrival has materialized; the rest still pending.
        assert len(game.materialized) == 1

        for _ in range(total):
            target = game.expected_disposition(game.active_case).value
            inspect_target = next(iter(game.presented_documents))
            _inspect(ledger, inspect_target)
            _choose(ledger, f"Choose {target}")

        assert ledger.cursor.label == "victory"
        content = " ".join(
            f.content
            for f in ledger.get_journal()
            if isinstance(f.content, str)
        )
        assert "shift complete" in content.lower()
        assert f"of {total}" in content
