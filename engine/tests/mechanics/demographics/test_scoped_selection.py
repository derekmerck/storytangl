"""World-visible naming definitions, explicit precedence, and origin mixtures."""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from uuid import uuid4

from pydantic import Field, ValidationError
import pytest

from tangl.core import Graph, Node, Selector, TokenCatalog
from tangl.mechanics.demographics import (
    Country, DemographicSampler, NameBank, NameForm, NamePart, NamePool, Origin,
    load_pack, name_catalog,
    register_pack, select_bank, select_origin,
)
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import World
from tangl.vm.runtime.frame import PhaseCtx


@dataclass
class NamingAssets:
    """A world-owned provider using World's existing asset catalog path."""

    names: TokenCatalog[NameBank]

    def get_token_catalogs(self, **_kwargs: object) -> list[TokenCatalog]:
        return [self.names]


class OriginHolder(Node):
    origin: Origin = Field(json_schema_extra={"unstructurable": True})


def bank(given: str, *, key: str | None = None) -> NameBank:
    return NameBank(
        label=f"scoped_{uuid4().hex}", selection_key=key,
        forms={"plain": NameForm(
            given=NamePart(pool=NamePool(candidates=[given])),
            family=NamePart(pool=NamePool(candidates=["Family"])),
        )},
    )


def world(catalog: TokenCatalog[NameBank]) -> World:
    return World.from_script_data(
        script_data={
            "label": f"naming_world_{uuid4().hex}",
            "metadata": {"start_at": "intro.start"},
            "scenes": {"intro": {"blocks": {"start": {"content": "Casting."}}}},
        },
        assets=NamingAssets(catalog),
    )


@pytest.mark.parametrize("order", [("A", "B"), ("B", "A")])
def test_two_real_worlds_resolve_the_same_local_key_without_import_order_leakage(
    order: tuple[str, str],
) -> None:
    builtin = register_pack(load_pack("sample"))
    original = NameBank.get_instance("fra")
    original_forms = dict(original.forms)
    worlds: dict[str, World] = {}
    chosen: dict[str, NameBank] = {}
    for label in order:
        chosen[label] = bank(label, key="fra")
        worlds[label] = world(name_catalog(builtin, overrides=(chosen[label],)))

    for label in order:
        authority = worlds[label]
        result = authority.create_story("cast")
        graph = result.graph
        ctx = PhaseCtx(graph=graph, cursor_id=graph.initial_cursor_id, random=Random(7))
        catalogs = ctx.get_token_catalogs()
        assert authority.resolve_token_definition(NameBank, "fra") is chosen[label]
        assert graph.resolve_token_definition(NameBank, "fra") is chosen[label]
        selection = select_origin(
            Origin(label="river", banks={"fra": 1}), catalogs=catalogs, rng=ctx.get_random(),
        )
        assert selection.bank is chosen[label]
        assert DemographicSampler.sample_name(
            selection.bank, form="plain", catalogs=catalogs, rng=Random(7),
        ).full_name() == f"{label} Family"
        assert select_bank("jpn", catalogs=catalogs) is NameBank.get_instance("jpn")
        assert Country.get_instance("fra").namebank(
            "european", catalogs=catalogs, fallback_bank="fra",
        ) is chosen[label]
        profile = DemographicSampler.sample_demographic(
            country="fra", rng=ctx.get_random(),
        )
        assert profile.country is Country.get_instance("fra")
        assert "given_name" not in type(profile).model_fields
        other = "B" if label == "A" else "A"
        with pytest.raises(LookupError):
            select_bank(chosen[other].label, catalogs=catalogs)
        with pytest.raises(LookupError):
            select_bank(original, catalogs=catalogs)
        with pytest.raises(LookupError):
            DemographicSampler.sample_name(
                original, form="female", catalogs=catalogs, rng=Random(7),
            )

    assert NameBank.get_instance("fra") is original
    assert original.forms == original_forms
    assert tuple(builtin.find_all()) == (original, NameBank.get_instance("jpn"))


def test_scope_rejects_global_references_live_objects_and_empty_catalogs() -> None:
    outside = bank("Outside")
    inside = bank("Inside")
    catalogs = [TokenCatalog(NameBank, members=(inside,))]
    for ref in (outside.label, outside):
        with pytest.raises(LookupError, match="supplied catalogs"):
            select_bank(ref, catalogs=catalogs)
    with pytest.raises(LookupError):
        select_bank(inside, catalogs=[])
    with pytest.raises(LookupError):
        select_bank(Selector(selection_key="unknown"), catalogs=catalogs, rng=Random(7))


def test_country_exact_audit_and_explicit_fallback_remain_distinct() -> None:
    catalog = register_pack(load_pack("sample"))
    france = Country.get_instance("fra")
    with pytest.raises(LookupError):
        france.namebank("european", catalogs=[catalog])
    assert france.namebank("european", catalogs=[catalog], fallback_bank="fra").label == "fra"
    with pytest.raises(LookupError):
        france.namebank("european", catalogs=[], fallback_bank="fra")
    assert ("fra", "european") in load_pack("sample").uncovered_subtypes()


def test_two_origins_keep_identity_while_borrowing_one_non_geographic_bank() -> None:
    custom = bank("Cookie", key="sprite")
    catalogs = [TokenCatalog(NameBank, members=(custom,))]
    origins = [Origin(label=label, banks={"sprite": 1}) for label in ("river", "north")]
    selections = [select_origin(origin, catalogs=catalogs, rng=Random(7)) for origin in origins]
    assert [selection.origin.label for selection in selections] == ["river", "north"]
    assert all(selection.bank is custom for selection in selections)
    assert DemographicSampler.sample_name(
        custom, form="plain", catalogs=catalogs, rng=Random(7),
    ).full_name() == "Cookie Family"


def test_selector_is_scoped_uniform_stable_and_deduplicates_repeat_offers() -> None:
    a, b, outside = bank("A", key="a"), bank("B", key="b"), bank("Outside", key="a")
    catalog = TokenCatalog(NameBank, members=(a, b))
    reverse = TokenCatalog(NameBank, members=(b, a))
    assert select_bank(Selector(selection_key="a"), catalogs=[catalog], rng=Random(1)) is a
    left, right = Random(42), Random(42)
    first = [select_bank(Selector(), catalogs=[catalog, catalog], rng=left) for _ in range(40)]
    second = [select_bank(Selector(), catalogs=[reverse], rng=right) for _ in range(40)]
    assert first == second
    assert set(first) == {a, b}
    assert outside not in first
    with pytest.raises(ValueError, match="explicit RNG"):
        select_bank(Selector(), catalogs=[catalog])


def test_weighted_origin_is_deterministic_with_stable_ref_order_and_zero_exclusion() -> None:
    a, b, zero = bank("A", key="a"), bank("B", key="b"), bank("Zero", key="zero")
    forward = TokenCatalog(NameBank, members=(a, zero, b))
    reverse = TokenCatalog(NameBank, members=(b, zero, a))
    one = Origin(label="one", banks={"a": 1, "b": 3, "zero": 0})
    two = Origin(label="two", banks={"zero": 0, "b": 3, "a": 1})
    left, right = Random(42), Random(42)
    first = [select_origin(one, catalogs=[forward], rng=left).bank for _ in range(40)]
    second = [select_origin(two, catalogs=[reverse], rng=right).bank for _ in range(40)]
    assert first == second
    assert [item.selection_key for item in first[:8]] == ["b", "a", "b", "a", "b", "b", "b", "a"]
    assert set(first) == {a, b}
    assert first.count(b) > first.count(a)
    huge = Origin(label="huge", banks={"a": 1e308, "b": 1e308})
    assert select_origin(huge, catalogs=[forward], rng=Random(42)).bank in {a, b}


@pytest.mark.parametrize("weight", [-1, float("nan"), float("inf"), -float("inf"), "1", True])
def test_invalid_origin_weights_fail(weight: object) -> None:
    with pytest.raises(ValidationError):
        Origin(label="invalid", banks={"unknown": weight})


def test_empty_zero_and_unknown_mixtures_fail_without_consuming_rng() -> None:
    known = bank("Known", key="known")
    catalogs = [TokenCatalog(NameBank, members=(known,))]
    with pytest.raises(ValidationError):
        Origin(label="empty", banks={})
    for mixture, error in (({"known": 0}, ValueError), ({"missing": 1}, LookupError),
                           ({"known": 1, "missing": 0}, LookupError)):
        rng = Random(7)
        before = rng.getstate()
        with pytest.raises(error):
            select_origin(Origin(label="bad", banks=mixture), catalogs=catalogs, rng=rng)
        assert rng.getstate() == before


def test_ambiguous_offers_fail_instead_of_using_catalog_or_import_order() -> None:
    a, b = bank("A", key="same"), bank("B", key="same")
    ca, cb = TokenCatalog(NameBank, members=(a,)), TokenCatalog(NameBank, members=(b,))
    for catalogs in ([ca, cb], [cb, ca]):
        with pytest.raises(ValueError, match="Ambiguous NameBank"):
            select_bank("same", catalogs=catalogs)
        with pytest.raises(ValueError, match="Ambiguous base naming key"):
            name_catalog(*catalogs)
    with pytest.raises(ValueError, match="Repeated naming override"):
        name_catalog(overrides=(a, b))
    for base in (ca, cb):
        composed = name_catalog(base, overrides=(b,))
        assert select_bank("same", catalogs=[composed]) is b


def test_origin_constructor_form_round_trips_through_json_without_bank_embedding() -> None:
    origin = Origin(label="river", banks={"fra": 1, "jpn": 3})
    graph = Graph()
    owner = OriginHolder(label="origin_holder", origin=origin)
    graph.add(owner)
    restored = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    restored_origin = restored.get(owner.uid).origin
    assert type(restored_origin) is Origin
    assert restored_origin.label == "river"
    assert restored_origin.banks == {"fra": 1, "jpn": 3}
    assert "fra" not in {item.label for item in restored.values()}


def test_compound_recipe_uses_real_world_context_and_origin_scope() -> None:
    builtin = register_pack(load_pack("sample"))
    recipe = NameBank(
        label=f"sprite_{uuid4().hex}", selection_key="fra",
        forms={"sprite": NameForm(
            given=NamePart(pool=NamePool(candidates=["Cookie"])),
            family=NamePart(pool=NamePool(candidates=["Winter"]),
                            suffix=NamePool(candidates=["mint"])),
        )},
    )
    authority = world(name_catalog(builtin, overrides=(recipe,)))
    graph = authority.create_story("sprites").graph
    ctx = PhaseCtx(graph=graph, cursor_id=graph.initial_cursor_id, random=Random(7))
    selected = select_origin(Origin(label="grove", banks={"fra": 1}),
                             catalogs=ctx.get_token_catalogs(), rng=ctx.get_random())
    assert selected.origin.label == "grove"
    assert selected.bank is recipe
    assert graph.resolve_token_definition(NameBank, "fra") is recipe
    assert DemographicSampler.sample_name(
        selected.bank, form="sprite", catalogs=ctx.get_token_catalogs(), rng=ctx.get_random(),
    ).full_name() == "Cookie Wintermint"
    with pytest.raises(LookupError):
        DemographicSampler.sample_name(
            recipe, form="sprite", catalogs=[builtin], rng=Random(7),
        )
