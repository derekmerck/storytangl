"""One owned personal name alongside durable facts through actual materialization."""
from __future__ import annotations

import os
from pathlib import Path
from random import Random
import subprocess
import sys
from uuid import uuid4

import pytest

from tangl.core import EntityTemplate, Selector
from tangl.lang.age_range import AgeRange
from tangl.lang.gens import Gens
from tangl.lang.personal_name import PersonalName
from tangl.mechanics.demographics import (
    Country, DemographicData, DemographicSampler, Region, Subtype,
)
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.prose.naming import NamingOperations
from tangl.story import StoryGraph, World
from tangl.vm import ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx

from pytest_helpers.demographic_actor import ProfileActor, bootstrap_world


@pytest.fixture
def materialized() -> tuple[World, StoryGraph, ProfileActor]:
    world = bootstrap_world(f"profile_world_{uuid4().hex}")
    catalogs = world.get_token_catalogs()
    name = DemographicSampler.sample_name(
        "fra", form="female", catalogs=catalogs, rng=Random(7),
    )
    profile = DemographicSampler.sample_demographic(
        country="fra", subtype="european", gender=Gens.X_,
        age_range=AgeRange.ADULT, rng=Random(7),
    )
    template = EntityTemplate.from_data({
        "kind": ProfileActor, "label": "guide", "personal_name": name,
        "demographic": profile,
    })
    world.templates.add(template)
    graph = world.create_story("cast").graph
    actor = graph.find_one(Selector(label="guide", has_kind=ProfileActor))
    assert type(actor) is ProfileActor
    assert actor is not template.payload
    assert actor.personal_name is not template.payload.personal_name
    assert actor.demographic is not template.payload.demographic
    assert actor.graph is graph
    return world, graph, actor


def assert_bound_profile(actor: ProfileActor) -> None:
    assert type(actor.personal_name) is PersonalName
    assert type(actor.demographic) is DemographicData
    assert actor.demographic.country is Country.get_instance("fra")
    assert actor.demographic.region is Region.get_instance("west_europe")
    assert actor.demographic.subtype is Subtype.get_instance("european")
    assert actor.demographic.gender is Gens.X_
    assert actor.demographic.age_range is AgeRange.ADULT
    assert actor.name == ""
    assert "name" not in actor.model_fields_set
    assert "given_name" not in type(actor.demographic).model_fields
    assert "personal_name" not in actor.demographic.unstructure()
    assert actor.get_ns()["demographic"] is actor.demographic
    assert actor.get_ns()["personal_name"] is actor.personal_name


@pytest.mark.parametrize("parts", [
    {"given_name": "Dana", "family_name": "Reyes"},
    {"given_name": "Cookie"},
    {"family_name": "Wintermint"},
])
def test_real_materialization_rename_and_json_preserve_one_name_owner(
    materialized: tuple[World, StoryGraph, ProfileActor], parts: dict[str, str],
) -> None:
    _world, _graph, source = materialized
    assert source.personal_name.full_name() == "Sophie Dubois"
    world = bootstrap_world(f"optional_name_world_{uuid4().hex}")
    world.templates.add(EntityTemplate.from_data({
        "kind": ProfileActor, "label": "guide", "demographic": source.demographic,
        "personal_name": PersonalName(**parts, title="", gender=Gens.X_),
    }))
    graph = world.create_story("optional_names").graph
    actor = graph.find_one(Selector(label="guide", has_kind=ProfileActor))
    assert type(actor) is ProfileActor
    before_profile = actor.demographic.unstructure()
    ctx = PhaseCtx(graph=graph, cursor_id=graph.initial_cursor_id,
                   current_phase=ResolutionPhase.JOURNAL, random=Random(13))
    rng_before = ctx.get_random().getstate()
    expected = " ".join(parts.values())
    for _ in range(2):
        ns = actor.get_ns()
        assert ns["full_name"] == expected
        assert ns["given_name"] == parts.get("given_name")
        assert ns["family_name"] == parts.get("family_name")
        assert NamingOperations(ctx).reference(actor, form="full") == expected
        assert NamingOperations(ctx).reference(actor) == actor.personal_name.name()
        assert ns["name"] == actor.personal_name.name()
        assert actor.demographic.unstructure() == before_profile
    assert ctx.get_random().getstate() == rng_before
    assert_bound_profile(actor)

    # Mutate the one existing name value; later inspection and prose see it.
    if "given_name" in parts:
        actor.personal_name.given_name = "Renamed"
    else:
        actor.personal_name.family_name = "Renamed"
    current = actor.personal_name.full_name()
    assert actor.get_ns()["full_name"] == current
    assert NamingOperations(ctx).reference(actor, form="full") == current
    assert actor.get_nominal() == actor.personal_name.name()
    assert ctx.get_random().getstate() == rng_before
    assert actor.demographic.unstructure() == before_profile

    data = graph.unstructure()
    restored = StoryGraph.structure(Json.deserialize(Json.serialize(data)))
    other = restored.get(actor.uid)
    assert other.uid == actor.uid
    assert other.graph is restored
    assert other.personal_name is not actor.personal_name
    assert other.personal_name.full_name() == current
    assert other.get_ns()["full_name"] == current
    assert_bound_profile(other)
    assert len(list(restored.find_all(Selector(has_kind=ProfileActor)))) == 1
    refs = other.demographic.unstructure()
    for key in ("country", "region", "subtype"):
        assert set(refs[key]) == {"kind", "label"}
    assert "forms" not in repr(refs)


def test_explicit_display_and_proper_forms_remain_intentional_overrides(
    materialized: tuple[World, StoryGraph, ProfileActor],
) -> None:
    _world, graph, actor = materialized
    actor.name = "The Guide"
    actor.proper_forms["full"] = "Captain Reed"
    actor.personal_name = PersonalName(given_name="Dana", family_name="Reyes", title="")
    ctx = PhaseCtx(graph=graph, cursor_id=graph.initial_cursor_id)
    assert actor.get_ns()["name"] == "The Guide"
    assert actor.get_ns()["full_name"] == "Captain Reed"
    assert NamingOperations(ctx).reference(actor) == "The Guide"
    assert NamingOperations(ctx).reference(actor, form="full") == "Captain Reed"
    actor.personal_name.given_name = "Ari"
    assert actor.get_nominal() == "The Guide"
    assert actor.get_nominal(form="full") == "Captain Reed"
    assert actor.personal_name.full_name() == "Ari Reyes"


def test_fresh_process_restores_actual_values_after_declared_bootstrap_without_sampling(
    materialized: tuple[World, StoryGraph, ProfileActor], tmp_path: Path,
) -> None:
    world, graph, actor = materialized
    actor.personal_name = PersonalName(given_name="Saved", family_name="Value", title="")
    actor.personal_name.aliases.add("Remembered")
    path = tmp_path / "graph.json"
    path.write_text(Json.serialize(graph.unstructure()), encoding="utf-8")
    script = '''
from pathlib import Path
import sys
from unittest.mock import patch
from uuid import UUID
from tangl.mechanics.demographics import Country, DemographicSampler, Region, Subtype
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import StoryGraph, World
from pytest_helpers.demographic_actor import ProfileActor, bootstrap_world

def forbidden(*_args, **_kwargs):
    raise AssertionError("Restoration must never sample")

methods = ("sample_name", "sample_demographic", "sample_region", "sample_country",
           "sample_subtype", "sample_gender", "sample_age_range")
with patch.multiple(DemographicSampler, **{name: forbidden for name in methods}):
    world = bootstrap_world(sys.argv[2])
    graph = StoryGraph.structure(Json.deserialize(Path(sys.argv[1]).read_text()))
    actor = graph.get(UUID(sys.argv[3]))
    assert graph.factory is world
    assert type(actor) is ProfileActor and actor.graph is graph
    assert actor.personal_name.full_name() == "Saved Value"
    assert actor.personal_name.aliases == {"Remembered"}
    assert actor.get_ns()["full_name"] == "Saved Value"
    assert actor.get_nominal() == "Saved"
    assert actor.demographic.country is Country.get_instance("fra")
    assert actor.demographic.region is Region.get_instance("west_europe")
    assert actor.demographic.subtype is Subtype.get_instance("european")
    assert actor.demographic.gender.value == "X_" and actor.demographic.age_range.value == 3
    assert "personal_name" not in actor.demographic.unstructure()
    assert actor.name == ""
'''
    test_root = str(Path(__file__).resolve().parents[2])
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        filter(None, (test_root, os.environ.get("PYTHONPATH"))),
    )}
    result = subprocess.run(
        [sys.executable, "-c", script, str(path), world.label, str(actor.uid)],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
