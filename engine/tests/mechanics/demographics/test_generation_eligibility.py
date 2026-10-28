"""Dependent candidate preparation must finish before generation draws."""
from __future__ import annotations

from collections.abc import Sequence
from random import Random
from uuid import uuid4

import pytest

from tangl.core import Graph
from tangl.lang.personal_name import PersonalName
from tangl.mechanics.demographics import (
    Country, DemographicData, GenerationReceipt, GenerationRequest, NameBank,
    NameForm, NamePart, NamePool, Origin, Region, Subtype, complete_generation,
    name_catalog,
)
from tangl.vm import ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx

from pytest_helpers.demographic_generation import bootstrap


def country(*, mix: dict[Subtype, int] | None = None) -> Country:
    return Country(
        label=f"eligibility_{uuid4().hex}", name="Fixture", demonym="Fixture",
        population=1, eth_mix=mix,
    )


def region(countries: list[Country], mix: dict[Subtype, int]) -> Region:
    return Region(
        label=f"eligibility_{uuid4().hex}", name="Fixture", demonym="Fixture",
        countries=set(countries), eth_mix=mix,
    )


def restrict(
    monkeypatch: pytest.MonkeyPatch, countries: list[Country], regions: list[Region],
) -> None:
    # Isolate only these queries; never clear process-global definitions.
    for cls, values in ((Country, countries), (Region, regions)):
        monkeypatch.setattr(cls, "all_instances", classmethod(lambda _cls, v=values: iter(v)))
        monkeypatch.setattr(cls, "find_all_instances", classmethod(
            lambda _cls, selector=None, v=values: selector.filter(v) if selector else iter(v),
        ))


class Controlled(Random):
    def __init__(self, bad: Country | Region | None = None) -> None:
        super().__init__(7)
        self.bad = bad
        self.offered = []

    def choices[T](
        self, values: Sequence[T], weights: Sequence[float] | None = None, *, k: int = 1,
    ) -> list[T]:
        self.offered.append(list(values))
        # Force the bad candidate if production erroneously offers it.
        return [self.bad if self.bad in values else values[0]]

    def choice[T](self, values: Sequence[T]) -> T:
        return self.choices(values)[0]


class NoDraw(Random):
    def choices[T](
        self, values: Sequence[T], weights: Sequence[float] | None = None, *, k: int = 1,
    ) -> list[T]:
        pytest.fail("Invalid candidates reached a draw")

    def choice[T](self, values: Sequence[T]) -> T:
        pytest.fail("Invalid candidates reached a draw")


def run(
    spec: GenerationRequest, profile: DemographicData | None = None, rng: Random | None = None,
) -> tuple[PersonalName | None, DemographicData, GenerationReceipt]:
    ctx = PhaseCtx(
        graph=Graph(), cursor_id=None, current_phase=ResolutionPhase.UPDATE,
        random=rng if rng is not None else Random(7),
    )
    return complete_generation(
        spec, personal_name=None, demographic=profile or DemographicData(), receipt=None, ctx=ctx,
    )


def test_region_generated_in_same_request_supplies_subtype(monkeypatch: pytest.MonkeyPatch) -> None:
    subtype = Subtype(label=f"eligibility_{uuid4().hex}")
    child = country()
    parent = region([child], {subtype: 1})
    restrict(monkeypatch, [child], [parent])
    spec = GenerationRequest(facts={"region", "subtype"})
    left, right = Random(9), Random(9)
    first = run(spec, rng=left)
    second = run(spec, rng=right)
    assert first[1].region is parent and first[1].subtype is subtype
    assert first[1].country is None
    assert first[1].unstructure() == second[1].unstructure()
    assert left.getstate() == right.getstate()
    assert first[2].generated == ["region", "subtype"]


@pytest.mark.parametrize("include_region", [False, True])
def test_orphan_country_is_never_offered_for_dependent_subtype(
    monkeypatch: pytest.MonkeyPatch, include_region: bool,
) -> None:
    subtype = Subtype(label=f"eligibility_{uuid4().hex}")
    orphan, good = country(), country(mix={subtype: 1})
    if include_region:
        bad_parent = region([orphan], {})
        good_parent = region([good], {subtype: 1})
        regions = [bad_parent, good_parent]
        bad = bad_parent
    else:
        regions = []
        bad = orphan
    restrict(monkeypatch, [orphan, good], regions)
    rng = Controlled(bad)
    facts = {"country", "subtype"} | ({"region"} if include_region else set())
    result = run(GenerationRequest(facts=facts), rng=rng)
    assert result[1].country is good and result[1].subtype is subtype
    assert all(bad not in values for values in rng.offered)


@pytest.mark.parametrize("branch", ["global", "pinned_region", "generated_region", "region_only"])
def test_no_eligible_dependent_candidates_fail_without_draws(
    monkeypatch: pytest.MonkeyPatch, branch: str,
) -> None:
    orphan = country()
    parent = region([orphan], {}) if branch != "global" else None
    restrict(monkeypatch, [orphan], [parent] if parent is not None else [])
    facts = {"subtype"} | ({"country"} if branch != "region_only" else set())
    if branch in {"generated_region", "region_only"}:
        facts.add("region")
    profile = DemographicData(region=parent) if branch == "pinned_region" else DemographicData()
    with pytest.raises((ValueError, LookupError), match="eligible|mixture"):
        run(GenerationRequest(facts=facts), profile=profile, rng=NoDraw())


def test_pinned_region_country_inherits_mix_and_pinned_subtype_needs_no_mix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subtype = Subtype(label=f"eligibility_{uuid4().hex}")
    child = country()
    parent = region([child], {subtype: 1})
    restrict(monkeypatch, [child], [parent])
    result = run(GenerationRequest(facts={"country", "subtype"}),
                 profile=DemographicData(region=parent))
    assert result[1].country is child and result[1].subtype is subtype
    orphan = country()
    restrict(monkeypatch, [orphan], [])
    result = run(GenerationRequest(facts={"country", "subtype"}),
                 profile=DemographicData(subtype=subtype), rng=Controlled())
    assert result[1].country is orphan and result[1].subtype is subtype


@pytest.mark.parametrize("missing_zero_ref", [False, True])
def test_origin_zero_weight_reference_must_exist_but_needs_no_unused_form(
    missing_zero_ref: bool,
) -> None:
    world = bootstrap(f"eligible_origin_{uuid4().hex}")
    plain = NameBank(label=f"plain_{uuid4().hex}", forms={"plain": NameForm(
        given=NamePart(pool=NamePool(candidates=["Unused"])),
    )})
    world.assets.names = name_catalog(world.assets.names, overrides=(plain,))
    graph = world.create_story("eligibility").graph
    ctx = PhaseCtx(graph=graph, cursor_id=graph.initial_cursor_id,
                   current_phase=ResolutionPhase.UPDATE, random=Random(7))
    spec = GenerationRequest(
        name_parts={"given_name": True}, form="female",
        origin=Origin(label="mixed", banks={
            "fra": 1, "missing" if missing_zero_ref else plain.label: 0,
        }),
    )
    before = ctx.get_random().getstate()
    if missing_zero_ref:
        with pytest.raises(LookupError):
            complete_generation(
                spec, personal_name=None, demographic=DemographicData(), receipt=None, ctx=ctx,
            )
        assert ctx.get_random().getstate() == before
    else:
        name, profile, receipt = complete_generation(
            spec, personal_name=None, demographic=DemographicData(), receipt=None, ctx=ctx)
        assert name.given_name in NameBank.get_instance("fra").forms["female"].given.pool.candidates
        assert receipt.bank is NameBank.get_instance("fra")
