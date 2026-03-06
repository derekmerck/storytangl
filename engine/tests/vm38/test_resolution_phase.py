"""Contract tests for ``tangl.vm.resolution_phase``."""

from __future__ import annotations

from tangl.vm.resolution_phase import ResolutionPhase


class TestResolutionPhaseOrdering:
    """Pipeline phase ordering is causal and stable."""

    def test_init_is_zero(self) -> None:
        assert ResolutionPhase.INIT == 0

    def test_phases_in_causal_order(self) -> None:
        P = ResolutionPhase
        assert P.VALIDATE < P.PLANNING < P.PREREQS < P.UPDATE
        assert P.UPDATE < P.JOURNAL < P.FINALIZE < P.POSTREQS

    def test_ordered_phases_excludes_init(self) -> None:
        phases = ResolutionPhase.ordered_phases()
        assert ResolutionPhase.INIT not in phases

    def test_ordered_phases_returns_seven(self) -> None:
        assert len(ResolutionPhase.ordered_phases()) == 7

    def test_ordered_phases_is_sorted(self) -> None:
        phases = ResolutionPhase.ordered_phases()
        assert phases == sorted(phases, key=lambda p: p.value)


class TestResolutionPhaseComparison:
    """Phases are IntEnum — comparisons drive entry_phase skipping."""

    def test_le_for_entry_phase_gating(self) -> None:
        """Frame uses ``entry_phase <= phase`` to decide whether to run."""
        assert ResolutionPhase.VALIDATE <= ResolutionPhase.VALIDATE
        assert ResolutionPhase.VALIDATE <= ResolutionPhase.PLANNING
        assert not (ResolutionPhase.PLANNING <= ResolutionPhase.VALIDATE)

    def test_phases_usable_as_dict_keys(self) -> None:
        d = {ResolutionPhase.VALIDATE: "ok"}
        assert d[ResolutionPhase.VALIDATE] == "ok"

    def test_phase_name_access(self) -> None:
        assert ResolutionPhase.JOURNAL.name == "JOURNAL"
        assert ResolutionPhase["JOURNAL"] is ResolutionPhase.JOURNAL
