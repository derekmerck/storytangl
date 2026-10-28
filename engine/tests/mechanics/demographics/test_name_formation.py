"""Complete and compound forms share one kernel without changing source spellings."""
from __future__ import annotations

from copy import deepcopy
from random import Random
from uuid import uuid4

from pydantic import Field, ValidationError
import pytest

from tangl.core import Graph, Node, TokenCatalog
from tangl.lang.gens import Gens
from tangl.lang.personal_name import PersonalName
from tangl.mechanics.demographics import (
    DemographicSampler, NameBank, NameForm, NamePart, NamePool, load_pack, parse_pack,
)
from tangl.persistence.serializers import JsonSerializationHandler as Json


class RecipeHolder(Node):
    form: NameForm = Field(json_schema_extra={"unstructurable": True})


def scoped_bank(form: NameForm) -> tuple[NameBank, list[TokenCatalog[NameBank]]]:
    bank = NameBank(label=f"formation_{uuid4().hex}", forms={"chosen": form})
    return bank, [TokenCatalog(NameBank, members=(bank,))]


def test_complete_human_name_uses_existing_personal_name_type() -> None:
    bank, catalogs = scoped_bank(NameForm(
        given=NamePart(pool=NamePool(candidates=["Dana", "Ari"])),
        family=NamePart(pool=NamePool(candidates=["Reyes", "Chen"])),
    ))
    name = DemographicSampler.sample_name(
        bank, form="chosen", catalogs=catalogs, rng=Random(7), gender=Gens.X_,
    )
    assert type(name) is PersonalName
    assert name.full_name() == "Ari Reyes"
    assert name.gender is Gens.X_


def test_sprite_stem_required_suffix_and_explicit_optional_suffix_absence() -> None:
    given = NamePart(pool=NamePool(candidates=["Cookie"]))
    stem = NamePool(candidates=["Winter"])
    for suffix, expected in ((NamePool(candidates=["mint"]), "Cookie Wintermint"),
                             (None, "Cookie Winter")):
        bank, catalogs = scoped_bank(NameForm(
            given=given, family=NamePart(pool=stem, suffix=suffix),
        ))
        name = DemographicSampler.sample_name(
            bank, form="chosen", catalogs=catalogs, rng=Random(7),
        )
        assert name.full_name() == expected


def test_substitutions_are_complete_stem_replacements_not_literal_suffixes() -> None:
    substitutions = {"Abelsdóttir": "Abelsson", "Adamcová": "Adamec"}
    given = NamePart(pool=NamePool(candidates=["Ari"]))
    for source, expected in substitutions.items():
        bank, catalogs = scoped_bank(NameForm(
            given=given,
            family=NamePart(pool=NamePool(candidates=[source]), substitutions=substitutions),
        ))
        name = DemographicSampler.sample_name(
            bank, form="chosen", catalogs=catalogs, rng=Random(7),
        )
        assert name.family_name == expected
    bank, catalogs = scoped_bank(NameForm(
        given=given,
        family=NamePart(
            pool=NamePool(candidates=["Adamcová"]), substitutions=substitutions,
            suffix=NamePool(candidates=["the Elder"]), suffix_separator=", ",
        ),
    ))
    assert DemographicSampler.sample_name(
        bank, form="chosen", catalogs=catalogs, rng=Random(7),
    ).family_name == "Adamec, the Elder"


def test_unicode_punctuation_case_prefixes_and_separators_survive() -> None:
    bank, catalogs = scoped_bank(NameForm(
        given=NamePart(pool=NamePool(candidates=["李・éVA"])),
        family=NamePart(
            pool=NamePool(candidates=["d'Arcy"]),
            prefix=NamePool(candidates=["van der"]), prefix_separator=" ",
            suffix=NamePool(candidates=["de la Lune"]), suffix_separator="—",
        ),
    ))
    name = DemographicSampler.sample_name(bank, form="chosen", catalogs=catalogs, rng=Random(7))
    assert name.full_name() == "李・éVA van der d'Arcy—de la Lune"


@pytest.mark.parametrize("part", ["given", "family"])
def test_single_names_and_arbitrary_forms_do_not_require_gender_or_geography(part: str) -> None:
    declaration = NameForm(**{part: NamePart(pool=NamePool(candidates=["Cookie"]))})
    bank, catalogs = scoped_bank(declaration)
    name = DemographicSampler.sample_name(bank, form="chosen", catalogs=catalogs, rng=Random(7))
    assert name.full_name() == "Cookie"
    assert name.gender is Gens.X_
    assert name.title == ""
    assert (name.given_name, name.family_name) == (
        ("Cookie", None) if part == "given" else (None, "Cookie")
    )


def test_form_selection_is_explicit_and_does_not_infer_from_gender() -> None:
    one = NameForm(given=NamePart(pool=NamePool(candidates=["One"])))
    two = NameForm(given=NamePart(pool=NamePool(candidates=["Two"])))
    bank = NameBank(label=f"forms_{uuid4().hex}", forms={"formal": one, "casual": two})
    catalogs = [TokenCatalog(NameBank, members=(bank,))]
    for gender in Gens:
        assert DemographicSampler.sample_name(
            bank, form="casual", gender=gender, catalogs=catalogs, rng=Random(7),
        ).given_name == "Two"
    rng = Random(7)
    before = rng.getstate()
    with pytest.raises(LookupError, match="has no form"):
        DemographicSampler.sample_name(bank, form="unknown", catalogs=catalogs, rng=rng)
    assert rng.getstate() == before


def test_weighted_candidate_positions_are_deterministic_and_zeroes_excluded() -> None:
    pool = NamePool(candidates=["A", "A", "B", "Zero"], weights=[1, 2, 1, 0])
    bank, catalogs = scoped_bank(NameForm(given=NamePart(pool=pool)))
    left, right = Random(42), Random(42)
    actual = [DemographicSampler.sample_name(
        bank, form="chosen", catalogs=catalogs, rng=left,
    ).given_name for _ in range(30)]
    repeated = [DemographicSampler.sample_name(
        bank, form="chosen", catalogs=catalogs, rng=right,
    ).given_name for _ in range(30)]
    assert actual == repeated
    assert actual[:8] == ["A", "A", "A", "A", "A", "A", "B", "A"]
    assert set(actual) == {"A", "B"}
    assert pool.candidates == ["A", "A", "B", "Zero"]
    huge, huge_scope = scoped_bank(NameForm(given=NamePart(
        pool=NamePool(candidates=["A", "B"], weights=[1e308, 1e308]),
    )))
    assert DemographicSampler.sample_name(
        huge, form="chosen", catalogs=huge_scope, rng=Random(42),
    ).given_name in {"A", "B"}


def test_unweighted_duplicates_keep_their_original_position_distribution() -> None:
    pool = NamePool(candidates=["A", "A", "B"])
    bank, catalogs = scoped_bank(NameForm(given=NamePart(pool=pool)))
    rng = Random(42)
    actual = [DemographicSampler.sample_name(
        bank, form="chosen", catalogs=catalogs, rng=rng,
    ).given_name for _ in range(8)]
    assert actual == ["B", "A", "A", "B", "A", "A", "A", "A"]
    assert pool.weights is None
    assert pool.candidates == ["A", "A", "B"]


@pytest.mark.parametrize("weights", [
    [1], [1, 2, 3], [0, 0], [-1, 1], [float("nan"), 1], [float("inf"), 1],
    [1, -float("inf")], [True, 1], ["1", 1],
])
def test_invalid_candidate_weight_domains_fail_at_declaration(weights: list[object]) -> None:
    with pytest.raises(ValidationError):
        NamePool(candidates=["A", "B"], weights=weights)


def test_empty_required_pools_forms_and_invalid_optional_affixes_fail_at_declaration() -> None:
    for candidates in ([], [""]):
        with pytest.raises(ValidationError):
            NamePool(candidates=candidates)
    with pytest.raises(ValidationError):
        NameForm()
    with pytest.raises(ValidationError):
        NameBank(label=f"empty_{uuid4().hex}", forms={})
    with pytest.raises(ValidationError):
        NamePart(pool={"candidates": ["Winter"]}, suffix={"candidates": []})
    with pytest.raises(ValidationError):
        NamePart(pool={"candidates": ["Winter"]}, suffix={"candidates": ["mint"], "weights": [0]})
    with pytest.raises(ValidationError):
        NamePart(pool={"candidates": ["Winter"]}, substitutions={"Winter": ""})


@pytest.mark.parametrize(("include_male", "male"), [(False, None), (True, None), (True, [])])
def test_legacy_absent_male_pool_becomes_an_explicit_shared_given_part(
    include_male: bool, male: list[str] | None,
) -> None:
    sample = load_pack("sample")
    raw = {"witness": {"female": ["Éva", "Éva", "李"],
                       "surname": ["Adamcová"], "male_surnames": {"Adamcová": "Adamec"}}}
    if include_male:
        raw["witness"]["male"] = male
    before = deepcopy(raw)
    parsed = parse_pack(sample.metadata, {"asia": sample.regions["asia"].model_dump()}, raw)
    forms = parsed.names["witness"]
    assert forms["male"].given is forms["female"].given
    assert forms["male"].given.pool.candidates == ["Éva", "Éva", "李"]
    assert forms["male"].family.substitutions == {"Adamcová": "Adamec"}
    assert forms["female"].family.substitutions == {}
    assert raw == before
    bank = NameBank(label=f"legacy_{uuid4().hex}", forms=forms)
    scope = [TokenCatalog(NameBank, members=(bank,))]
    assert DemographicSampler.sample_name(
        bank, form="male", catalogs=scope, rng=Random(7),
    ).family_name == "Adamec"
    assert set(NameBank.model_fields) >= {"forms", "selection_key"}
    assert not {"xx_names", "xy_names", "surname", "xy_surname"} & set(NameBank.model_fields)


def test_nested_recipe_values_use_existing_json_constructor_form_markers() -> None:
    form = NameForm(
        given=NamePart(pool=NamePool(candidates=["Cookie"], weights=[1])),
        family=NamePart(
            pool=NamePool(candidates=["Winter"]), suffix=NamePool(candidates=["mint"]),
            prefix=NamePool(candidates=["de"]), prefix_separator=" ",
        ),
    )
    # Inclusion retains changes to a default mapping on this owned value.
    form.family.substitutions["Winter"] = "Summer"
    graph = Graph()
    owner = RecipeHolder(label="recipe_owner", form=form)
    graph.add(owner)
    restored = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    recipe = restored.get(owner.uid).form
    assert type(recipe) is NameForm
    assert type(recipe.given) is NamePart
    assert type(recipe.family.pool) is NamePool
    assert type(recipe.family.prefix) is NamePool
    assert type(recipe.family.suffix) is NamePool
    assert recipe.given.pool.weights == [1]
    assert recipe.family.substitutions == {"Winter": "Summer"}
    bank, catalogs = scoped_bank(recipe)
    assert DemographicSampler.sample_name(
        bank, form="chosen", catalogs=catalogs, rng=Random(7),
    ).full_name() == "Cookie de Summermint"
    assert len(restored) == 1
