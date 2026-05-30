"""Story-info side-channel contracts for the credentials shift (Bridge.2b).

Exercises the advertise / get_story_info dispatch handlers and the disclosure
discipline: rules are public, progress shows the player's own rulings without
correctness, and case_summary shows only surfaced findings.
"""

from __future__ import annotations

from tangl.core import Graph

# Importing the module registers its dispatch handlers.
import tangl.mechanics.games.credentials_story_info  # noqa: F401
from tangl.mechanics.games import (
    CredentialCase,
    CredentialDisposition,
    CredentialStatus,
    CredentialToken,
    CredentialsGame,
    CredentialsGameHandler,
    HasGame,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
)
from tangl.service.dispatch import do_advertise_info_channels, do_get_story_info
from tangl.service.response import KvListValue, ScalarValue, StoryInfoRequest, TableValue
from tangl.story import Block
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.runtime.ledger import Ledger

D = CredentialDisposition
IND = Indication
S = CredentialStatus
L = RestrictionLevel

RULES = Restrictions.from_map(
    {Region.LOCAL: {IND.TRAVEL: L.WITH_ID, IND.WORK: L.WITH_PERMIT}}
)


class CredentialsBlock(HasGame, Block):
    _game_class = CredentialsGame
    _game_handler_class = CredentialsGameHandler


def _roster() -> list[CredentialCase]:
    return [
        CredentialCase(
            candidate_name="Edda Marrow",
            presented_documents={"passport": "A worn passport."},
            hidden_facts={"passport": "The seal is wrong for this border."},
            region=Region.LOCAL,
            purpose=IND.TRAVEL,
            id_card=CredentialToken(indication=IND.TRAVEL, status=S.MISSING_SEAL),
        ),
        CredentialCase(
            candidate_name="Tomas Vey",
            presented_documents={"passport": "A crisp passport."},
            region=Region.LOCAL,
            purpose=IND.TRAVEL,
            id_card=CredentialToken(indication=IND.TRAVEL, status=S.VALID),
        ),
    ]


def _block_and_ctx() -> tuple[CredentialsBlock, PhaseCtx]:
    graph = Graph(label="credentials_info")
    block = graph.add_node(kind=CredentialsBlock, label="checkpoint")
    block.game.roster = _roster()
    block.game.restriction_map = RULES
    block.game_handler.setup(block.game)
    ledger = Ledger.from_graph(graph, entry_id=block.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid, step=ledger.step)
    return block, ctx


def _sections(block, ctx, **request_kwargs):
    state = do_get_story_info(block, ctx=ctx, request=StoryInfoRequest(**request_kwargs))
    return {section.section_id: section for section in state.sections}


class TestAdvertise:
    def test_advertises_three_channels(self) -> None:
        block, ctx = _block_and_ctx()
        kinds = {a.kind for a in do_advertise_info_channels(block, ctx=ctx)}
        assert kinds == {"rules", "roster_progress", "case_summary"}

    def test_non_credentials_caller_advertises_nothing(self) -> None:
        graph = Graph(label="plain")
        plain = graph.add_node(kind=Block, label="plain")
        ledger = Ledger.from_graph(graph, entry_id=plain.uid)
        ctx = PhaseCtx(graph=graph, cursor_id=plain.uid, step=ledger.step)
        assert do_advertise_info_channels(plain, ctx=ctx) == []


class TestRulesChannel:
    def test_rules_project_the_restriction_map(self) -> None:
        block, ctx = _block_and_ctx()
        sections = _sections(block, ctx, kind="rules")
        value = sections["credential_rules"].value
        assert isinstance(value, KvListValue)
        pairs = {(row.key, row.value) for row in value.items}
        assert ("travel (local)", "with_id") in pairs
        assert ("work (local)", "with_permit") in pairs


class TestProgressChannel:
    def test_progress_scalar_before_any_ruling(self) -> None:
        block, ctx = _block_and_ctx()
        sections = _sections(block, ctx, kind="roster_progress")
        assert isinstance(sections["credential_progress"].value, ScalarValue)
        assert sections["credential_progress"].value.value == "Candidate 1 of 2"
        # No rulings table yet.
        assert "credential_rulings" not in sections

    def test_progress_shows_rulings_without_correctness(self) -> None:
        block, ctx = _block_and_ctx()
        handler = block.game_handler
        handler.receive_move(block.game, ("inspect", "passport"))
        handler.receive_move(block.game, ("decide", "pass"))  # wrong (should be deny)

        sections = _sections(block, ctx, kind="roster_progress")
        rulings = sections["credential_rulings"].value
        assert isinstance(rulings, TableValue)
        # The ruling is disclosed; correctness is not.
        assert rulings.columns == ["Candidate", "Your ruling"]
        assert rulings.rows == [["Edda Marrow", "pass"]]
        flat = str(rulings.model_dump()).lower()
        assert "correct" not in flat and "expected" not in flat


class TestCaseSummaryChannel:
    def test_empty_before_inspection(self) -> None:
        block, ctx = _block_and_ctx()
        sections = _sections(block, ctx, kind="case_summary")
        assert "credential_case_summary" not in sections

    def test_discloses_only_revealed_findings(self) -> None:
        block, ctx = _block_and_ctx()
        block.game_handler.receive_move(block.game, ("inspect", "passport"))

        sections = _sections(block, ctx, kind="case_summary")
        value = sections["credential_case_summary"].value
        assert isinstance(value, KvListValue)
        keys = {row.key for row in value.items}
        assert "passport" in keys
        # The expected disposition (hidden truth) never appears.
        flat = str(value.model_dump()).lower()
        assert "deny" not in flat and "expected" not in flat
