"""Pure selection, rule and palette resolution."""
from pathlib import Path

from tangl.media.media_creators.svg_forge.svg_catalog import SvgGroupDeclaration, index_svg_catalog
from tangl.media.media_creators.svg_forge.svg_plan import Operation, Recipe, Rule, resolve_plan
from tangl.media.media_resource.resource_manager import ResourceManager


def make_catalog(tmp_path: Path):
    source = tmp_path / "parts.svg"
    source.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
                      '<g id="frog"/><g id="pants"/><g id="dress"/><g id="sword"/>'
                      '<g id="grip"/><g id="hair"/><g id="hat"/><g id="horn"/></svg>')
    rit = ResourceManager(tmp_path).register_file(source)
    declarations = tuple(SvgGroupDeclaration(key=key, source_id=key, order=1,
                          aliases=("frock",) if key == "dress" else ())
                         for key in ("frog", "pants", "dress", "sword", "grip", "hair", "hat", "horn"))
    return index_svg_catalog(rit, declarations, channels=frozenset({"ink", "accent"}),
                             palettes={"day": {"ink": {"fill": "red"}}})


def test_alias_order_remove_readd_substitute_and_palette_provenance(tmp_path: Path) -> None:
    catalog = make_catalog(tmp_path)
    recipe = Recipe(selections=("frog", "frock", "dress", "hair"), palette="day",
                    overrides={"ink": {"fill": "blue"}})
    ops = (Operation(kind="remove", target="frock"), Operation(kind="add", target="dress"),
           Operation(kind="substitute", target="hair", replacement="hat", reason="changed"))
    before = recipe.model_dump(), catalog.digest
    plan = resolve_plan(catalog, recipe, palettes={"day": {"ink": {"fill": "red"}}},
                        defaults={"ink": {"fill": "white", "opacity": "0.5"}}, operations=ops)
    assert plan.ok
    assert [e.key for e in plan.entries] == ["frog", "dress", "hat"]
    assert plan.canonical_selections == ("frog", "dress", "hair")
    alias_recipe = recipe.model_copy(update={"selections": ("frog", "dress", "hair")})
    alias_plan = resolve_plan(catalog, alias_recipe, palettes={"day": {"ink": {"fill": "red"}}},
                              defaults={"ink": {"fill": "white", "opacity": "0.5"}},
                              operations=ops)
    assert alias_plan.identity == plan.identity
    canonical_ops = (Operation(kind="remove", target="dress"), ops[1], ops[2])
    canonical_plan = resolve_plan(catalog, recipe, palettes={"day": {"ink": {"fill": "red"}}},
                                  defaults={"ink": {"fill": "white", "opacity": "0.5"}},
                                  operations=canonical_ops)
    assert canonical_plan.identity == plan.identity
    assert plan.bindings["ink"] == {"fill": "blue", "opacity": "0.5"}
    assert plan.binding_sources["ink"] == {"fill": "override", "opacity": "default"}
    assert (recipe.model_dump(), catalog.digest) == before
    assert plan.identity == resolve_plan(catalog, recipe, palettes={"day": {"ink": {"fill": "red"}}},
        defaults={"ink": {"fill": "white", "opacity": "0.5"}}, operations=ops).identity
    changed = recipe.model_copy(update={"overrides": {"ink": {"fill": "green"}}})
    assert resolve_plan(catalog, changed, palettes={"day": {"ink": {"fill": "red"}}}).identity != plan.identity


def test_world_authored_exclusion_requirements_and_suppression(tmp_path: Path) -> None:
    catalog = make_catalog(tmp_path)
    palettes = {"day": {"ink": {"fill": "red"}}}
    rules = (
        Rule(name="frog trousers", when=("frog",), exclude=("pants",)),
        Rule(name="sword grip", when=("sword",), require=("grip",)),
        Rule(name="horned hats", when=("horn",), exclude=("hat",)),
        Rule(name="hat hair", when=("hat",), operations=(
            Operation(kind="suppress", target="hair", reason="hat covers hair"),)),
    )
    bad = Recipe(selections=("frog", "pants", "sword"), facts=("frog", "pants", "sword"), palette="day")
    result = resolve_plan(catalog, bad, palettes=palettes, rules=rules)
    assert not result.ok and result.entries == ()
    assert {(d.code, d.subject) for d in result.diagnostics} == {
        ("excluded", "frog trousers"), ("requirement", "sword grip")}
    good = Recipe(selections=("frog", "dress", "hair", "hat"), facts=("frog", "hat"), palette="day")
    result = resolve_plan(catalog, good, palettes=palettes, rules=rules)
    assert result.ok and "hair" not in [e.key for e in result.entries]
    assert "hair" in result.recipe.selections and result.decisions == ("hat covers hair",)
    horned = good.model_copy(update={"facts": ("frog", "hat", "horn")})
    assert any(d.subject == "horned hats" for d in resolve_plan(catalog, horned, palettes=palettes, rules=rules).diagnostics)
    permissive = tuple(rule for rule in rules if rule.name != "frog trousers")
    assert not any(d.subject == "frog trousers" for d in resolve_plan(catalog, bad, palettes=palettes, rules=permissive).diagnostics)


def test_missing_conflicts_and_invalid_palette_do_not_produce_partial_plan(tmp_path: Path) -> None:
    catalog = make_catalog(tmp_path)
    recipe = Recipe(selections=("hair", "missing"), palette="day", overrides={"ink": {"opacity": "2"}})
    ops = (Operation(kind="remove", target="hair"), Operation(kind="remove", target="hair"))
    plan = resolve_plan(catalog, recipe, palettes={"day": {"ink": {"fill": "red"}}}, operations=ops)
    assert not plan.ok and not plan.entries
    assert {d.code for d in plan.diagnostics} >= {"missing_reference", "conflicting_rule", "malformed_palette_binding"}


def test_missing_grip_is_coverage_not_a_mutation_or_global_prohibition(tmp_path: Path) -> None:
    catalog = make_catalog(tmp_path)
    palettes = {"day": {"ink": {"fill": "red"}}}
    recipe = Recipe(selections=("frog", "dress", "sword", "large-frog-grip"),
                    facts=("frog", "sword", "grip"), palette="day")
    rules = (Rule(name="sword needs grip", when=("sword",), require=("grip",)),)
    result = resolve_plan(catalog, recipe, palettes=palettes, rules=rules)
    assert [(d.code, d.subject) for d in result.diagnostics] == [
        ("missing_reference", "large-frog-grip"),
    ]
    assert "sword" in result.recipe.selections and result.entries == ()


def test_error_catalog_and_invalid_override_cannot_succeed(tmp_path: Path) -> None:
    catalog = make_catalog(tmp_path)
    from tangl.media.media_creators.svg_forge.svg_catalog import SvgCatalogDiagnostic

    invalid = catalog.model_copy(update={"diagnostics": (
        SvgCatalogDiagnostic(code="missing_group", subject="lost", detail="lost"),
    )})
    recipe = Recipe(selections=("dress",), palette="day", overrides={"unknown": {"fill": "red"}})
    result = resolve_plan(invalid, recipe, palettes={"day": {"ink": {"fill": "red"}}})
    assert not result.ok and not result.entries
    assert {d.code for d in result.diagnostics} == {"missing_group", "undeclared_palette_channel"}


def test_unique_alias_with_colliding_canonical_key_returns_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "parts.svg"
    source.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
                      '<g id="a"/><g id="b"/></svg>')
    rit = ResourceManager(tmp_path).register_file(source)
    catalog = index_svg_catalog(rit, (
        SvgGroupDeclaration(key="x", source_id="a", aliases=("unique",)),
        SvgGroupDeclaration(key="y", source_id="b", aliases=("x",)),
    ))
    recipe = Recipe(selections=("unique",), palette="day")
    before = recipe.model_dump(), catalog.model_dump()

    plan = resolve_plan(catalog, recipe, palettes={"day": {}})

    assert not plan.ok and plan.entries == ()
    assert any(d.code == "key_collision" and d.subject == "x" for d in plan.diagnostics)
    assert (recipe.model_dump(), catalog.model_dump()) == before


def test_independent_figure_overrides_do_not_leak(tmp_path: Path) -> None:
    catalog = make_catalog(tmp_path)
    palettes = {"day": {"ink": {"fill": "red"}}}
    first = Recipe(selections=("dress",), palette="day", overrides={"ink": {"fill": "blue"}})
    second = Recipe(selections=("dress",), palette="day")
    first_plan = resolve_plan(catalog, first, palettes=palettes)
    second_plan = resolve_plan(catalog, second, palettes=palettes)
    assert first_plan.bindings["ink"]["fill"] == "blue"
    assert second_plan.bindings["ink"]["fill"] == "red"
    assert palettes == {"day": {"ink": {"fill": "red"}}}
    assert first_plan.identity != second_plan.identity


def test_policy_revision_changes_identity(tmp_path: Path) -> None:
    catalog = make_catalog(tmp_path)
    recipe = Recipe(selections=("dress",), palette="day")
    palettes = {"day": {"ink": {"fill": "red"}}}
    first = resolve_plan(catalog, recipe, palettes=palettes, policy_revision="one")
    second = resolve_plan(catalog, recipe, palettes=palettes, policy_revision="two")
    assert first.ok and second.ok and first.identity != second.identity


def test_conflicting_substitutions_report_error(tmp_path: Path) -> None:
    catalog = make_catalog(tmp_path)
    recipe = Recipe(selections=("hair",), facts=("change",), palette="day")
    rules = (
        Rule(name="one", when=("change",), operations=(
            Operation(kind="substitute", target="hair", replacement="hat"),
        )),
        Rule(name="two", when=("change",), operations=(
            Operation(kind="substitute", target="hair", replacement="horn"),
        )),
    )
    plan = resolve_plan(catalog, recipe, palettes={"day": {"ink": {"fill": "red"}}}, rules=rules)
    assert not plan.ok and not plan.entries
    assert [(item.code, item.subject, item.detail) for item in plan.diagnostics] == [
        ("conflicting_rule", "hair", "Conflicting substitutions"),
    ]
