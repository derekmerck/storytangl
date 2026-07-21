"""Tests for roster sampling and lazy offer materialization (Phase A.3)."""

from __future__ import annotations

import random

import pytest

from tangl.mechanics.games import (
    CredentialDisposition,
    CredentialStatus,
    CredentialToken,
    CredentialsGame,
    CredentialsGameHandler,
    FailureMode,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
    ScenarioOffer,
    ShiftSpec,
    derive_disposition,
    generate_roster,
    materialize,
)

D = CredentialDisposition
IND = Indication
L = RestrictionLevel

RULES = Restrictions.from_map(
    {
        Region.LOCAL: {IND.TRAVEL: L.WITH_ID, IND.WORK: L.WITH_PERMIT, IND.WEAPON: L.WITH_PERMIT},
        Region.FOREIGN_WEST: {IND.TRAVEL: L.WITH_PERMIT, IND.WORK: L.FORBIDDEN, IND.WEAPON: L.FORBIDDEN},
    }
)


def _spec(**overrides) -> ShiftSpec:
    base = dict(rules=RULES, encounters=6, seed=42)
    base.update(overrides)
    return ShiftSpec(**base)


class TestGenerateRoster:
    def test_roster_has_requested_size(self) -> None:
        assert len(generate_roster(_spec(encounters=6))) == 6

    def test_pinned_offers_are_included(self) -> None:
        pin = ScenarioOffer(candidate_name="John Smith", target_disposition=D.PASS)
        roster = generate_roster(_spec(encounters=5, pinned=[pin]))
        assert len(roster) == 5
        assert any(o.candidate_name == "John Smith" for o in roster)

    def test_origin_distribution_is_honored(self) -> None:
        roster = generate_roster(_spec(origin_distribution={Region.FOREIGN_WEST: 1.0}))
        assert all(offer.region is Region.FOREIGN_WEST for offer in roster)

    def test_disposition_distribution_is_honored(self) -> None:
        roster = generate_roster(_spec(disposition_distribution={D.ARREST: 1.0}))
        assert all(offer.target_disposition is D.ARREST for offer in roster)

    def test_seed_is_reproducible(self) -> None:
        a = generate_roster(_spec(seed=7))
        b = generate_roster(_spec(seed=7))
        assert [o.model_dump() for o in a] == [o.model_dump() for o in b]

    def test_rejects_an_unsatisfiable_allowed_failure_policy(self) -> None:
        spec = _spec(
            encounters=1,
            origin_distribution={Region.LOCAL: 1.0},
            purpose_pool=[IND.WORK],
            disposition_distribution={D.ARREST: 1.0},
            allowed_failure_modes=[FailureMode.MISSING_PERMIT],
        )

        with pytest.raises(ValueError, match="No configured purpose"):
            generate_roster(spec)


class TestLinchpinInvariant:
    """Every materialized offer derives to the disposition it was generated for."""

    def test_mixed_distribution_round_trips(self) -> None:
        spec = _spec(
            encounters=30,
            origin_distribution={Region.LOCAL: 0.6, Region.FOREIGN_WEST: 0.4},
            disposition_distribution={D.PASS: 0.4, D.DENY: 0.3, D.ARREST: 0.3},
            seed=99,
        )
        for offer in generate_roster(spec):
            case = materialize(offer, RULES)
            assert derive_disposition(case.packet_manager, RULES) is offer.target_disposition

    def test_declared_with_id_contraband_reuses_the_purpose_id(self) -> None:
        rules = Restrictions.from_map(
            {
                Region.LOCAL: {
                    IND.TRAVEL: L.WITH_ID,
                    IND.WEAPON: L.WITH_ID,
                }
            }
        )

        spec = ShiftSpec(
            rules=rules,
            encounters=1,
            origin_distribution={Region.LOCAL: 1.0},
            purpose_pool=(IND.TRAVEL,),
            disposition_distribution={D.DENY: 1.0},
            allowed_failure_modes=(FailureMode.UNPERMITTED_CONTRABAND,),
        )

        with pytest.raises(ValueError, match="No configured purpose"):
            generate_roster(spec)


class TestMaterialize:
    def test_is_deterministic(self) -> None:
        offer = generate_roster(_spec(disposition_distribution={D.DENY: 1.0}))[0]
        first = materialize(offer, RULES)
        second = materialize(offer, RULES)
        assert first.candidate_name == second.candidate_name
        assert first.packet_manager.get_region() == second.packet_manager.get_region()
        assert first.packet_manager.get_purpose() == second.packet_manager.get_purpose()
        assert first.packet_manager.all_credentials() == second.packet_manager.all_credentials()

    def test_materialized_case_is_inspectable(self) -> None:
        offer = ScenarioOffer(region=Region.LOCAL, purpose=IND.WORK, target_disposition=D.PASS)
        case = materialize(offer, RULES)
        # A work candidate presents a passport and a work permit to inspect.
        assert "passport" in case.presented_documents
        assert any("permit" in label for label in case.presented_documents)

    def test_narrative_overrides_are_preserved(self) -> None:
        offer = ScenarioOffer(
            candidate_name="Pinned",
            target_disposition=D.PASS,
            presented_documents_override={"passport": "An authored passport."},
        )
        assert materialize(offer, RULES).presented_documents == {
            "passport": "An authored passport."
        }


class TestWhitelistedPin:
    """John Smith: an invalid packet that is waved through by a whitelist override."""

    def test_whitelist_override_beats_derivation(self) -> None:
        offer = ScenarioOffer(
            candidate_name="John Smith",
            region=Region.LOCAL,
            purpose=IND.WORK,
            target_disposition=D.ARREST,
            failure_modes=[FailureMode.FORGED_PERMIT],
            whitelist=True,
        )
        case = materialize(offer, RULES)
        game = CredentialsGame(offers=[offer], restriction_map=RULES)
        # The packet itself is criminal...
        assert derive_disposition(case.packet_manager, RULES) is D.ARREST
        # ...but the whitelist override makes the *expected* call an allow.
        assert game.expected_disposition(case) is D.PASS


class TestGameWalksOffers:
    def test_lazy_shift_completes_with_correct_calls(self) -> None:
        # An all-deny shift of work candidates with inspectable permit flaws.
        spec = _spec(
            encounters=3,
            origin_distribution={Region.LOCAL: 1.0},
            purpose_pool=[IND.WORK],
            disposition_distribution={D.DENY: 1.0},
            seed=5,
        )
        offers = generate_roster(spec)
        game = CredentialsGame(offers=offers, restriction_map=RULES)
        handler = CredentialsGameHandler()
        handler.setup(game)

        assert game.materialized == []  # nothing materialized until arrival
        assert game._total_cases() == 3

        for _ in range(3):
            _ = game.active_case  # arrival materializes this candidate
            inspect = handler.get_available_inspect_targets(game)[0]
            handler.receive_move(game, ("inspect", inspect))
            handler.receive_move(game, ("decide", "deny"))

        assert game.shift_complete
        assert game.result.name == "WIN"
        assert game.correct_count == 3

        # The shift summary counts the offers (3), not the default roster (2).
        summary = " ".join(f.content for f in handler.get_journal_fragments(game))
        assert "of 3" in summary
