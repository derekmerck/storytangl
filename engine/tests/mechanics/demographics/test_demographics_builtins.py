"""Explicit pack availability, pure parsing, repeat loading, and honest coverage."""
from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
from pathlib import Path
import subprocess
import sys
from random import Random

from pydantic import ValidationError
import pytest
import yaml

from tangl.mechanics.demographics import (
    Country, DemographicPack, DemographicSampler, NameBank, NameForm, NamePart, NamePool,
    PackUnavailableError, Region, Subtype,
    load_pack, parse_pack, register_pack,
)
from tangl.mechanics.demographics import packs


@pytest.fixture
def sample() -> DemographicPack:
    return load_pack("sample")


def test_parsing_is_pure_and_repeat_registration_preserves_references(sample: DemographicPack) -> None:
    resources = files(packs.__package__).joinpath("resources")
    geography = yaml.safe_load(resources.joinpath("nationalities.yaml").read_text())
    names = yaml.safe_load(resources.joinpath("sample_names.yaml").read_text())
    before = deepcopy((geography, names))
    parsed = parse_pack(sample.metadata, geography, names)
    assert (geography, names) == before
    assert parsed == sample
    unrelated = NameBank(label="unrelated_pack_witness", forms={"plain": NameForm(
        given=NamePart(pool=NamePool(candidates=["Only"])),
        family=NamePart(pool=NamePool(candidates=["Here"])),
    )})
    catalog = register_pack(parsed)
    country = Country.get_instance("fra")
    region = Region.get_instance("west_europe")
    bank = NameBank.get_instance("fra")
    register_pack(load_pack("sample"))
    assert Country.get_instance("fra") is country
    assert Region.get_instance("west_europe") is region
    assert NameBank.get_instance("fra") is bank
    assert NameBank.get_instance("unrelated_pack_witness") is unrelated
    assert (geography, names) == before
    name = DemographicSampler.sample_name(bank, form="female", catalogs=[catalog], rng=Random(7))
    assert (name.given_name, name.family_name) in [
        (given, family) for given in names["fra"]["female"] for family in names["fra"]["surname"]
    ]


def test_historical_geography_and_illustrative_pools_are_preserved(sample: DemographicPack) -> None:
    register_pack(sample)
    assert Country.get_instance("ago").population == 31825295
    assert Country.get_instance("ago").demonym == "Angolan"
    assert Region.get_instance("africa").population == 1109541977
    assert sample.names["fra"]["female"].given.pool.candidates == ["Marie", "Sophie", "Camille"]
    assert sample.names["jpn"]["male"].given.pool.candidates == ["Haruto", "Ren", "Yuto"]
    assert set(sample.names) == {"fra", "jpn"}
    with pytest.raises(LookupError, match="No eligible NameBank"):
        Country.get_instance("ago").namebank(catalogs=[register_pack(sample)])


def test_coverage_audit_does_not_assume_base_banks_cover_exact_subtypes(sample: DemographicPack) -> None:
    assert len(sample.countries_without_banks()) == 213
    assert "ago" in sample.countries_without_banks()
    assert "fra" not in sample.countries_without_banks()
    assert len(sample.uncovered_subtypes()) == 978
    assert ("fra", "european") in sample.uncovered_subtypes()
    assert ("usa", "black") in sample.uncovered_subtypes()
    assert sample.uncovered_subtypes() == load_pack("sample").uncovered_subtypes()


@pytest.mark.parametrize("pack", ["sample", "full"])
def test_metadata_identifies_source_revision_and_known_gaps(pack: str) -> None:
    metadata = packs.PackMetadata.model_validate(packs._read_yaml(f"{pack}_metadata.yaml"))
    assert metadata.label == pack
    assert metadata.revision
    assert metadata.source
    assert "2021" in metadata.geography
    assert metadata.transformations
    assert metadata.provenance_gaps


@pytest.mark.parametrize("full_state", ["absent", "pointer"])
def test_fresh_import_neither_reads_full_pack_nor_registers_definitions(
    tmp_path: Path, full_state: str,
) -> None:
    resources = files(packs.__package__).joinpath("resources")
    for name in ("sample_names.yaml", "sample_metadata.yaml", "full_metadata.yaml",
                 "nationalities.yaml"):
        (tmp_path / name).write_text(resources.joinpath(name).read_text())
    if full_state == "pointer":
        (tmp_path / "world_names.yaml").write_text(
            "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123\n"
        )
    script = '''
import importlib.resources
from pathlib import Path
import sys
from random import Random
original = importlib.resources.files
reads = []
def resources(package):
    if package == "tangl.mechanics.demographics":
        reads.append(package)
        return Path(sys.argv[1])
    return original(package)
importlib.resources.files = resources
from tangl.mechanics.demographics import (
    Country, NameBank, Region, Subtype, PackUnavailableError, load_pack, register_pack,
)
assert reads == []
assert all(not list(cls.all_instances()) for cls in (Country, NameBank, Region, Subtype))
# _read_yaml joins resources/ below the package root.
try:
    load_pack("full")
except PackUnavailableError as exc:
    assert "world_names.yaml" in str(exc)
else:
    raise AssertionError("Missing full data was accepted")
assert all(not list(cls.all_instances()) for cls in (Country, NameBank, Region, Subtype))
register_pack(load_pack("sample"))
assert set(NameBank.all_instance_labels()) == {"fra", "jpn"}
'''
    root = tmp_path / "package"
    root.mkdir()
    # Keep the fixture resource layout identical to the installed package.
    (root / "resources").symlink_to(tmp_path, target_is_directory=True)
    result = subprocess.run(
        [sys.executable, "-c", script, str(root)], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("contents", ["[broken", "- wrong shape", "fra: {female: []}"])
def test_malformed_actual_full_data_is_never_unavailable_or_sample(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contents: str,
) -> None:
    root = tmp_path / "resources"
    root.mkdir()
    resources = files(packs.__package__).joinpath("resources")
    for name in ("full_metadata.yaml", "nationalities.yaml"):
        (root / name).write_text(resources.joinpath(name).read_text())
    (root / "world_names.yaml").write_text(contents)
    monkeypatch.setattr(packs, "files", lambda _package: tmp_path)
    with pytest.raises((yaml.YAMLError, ValidationError)):
        load_pack("full")


def test_invalid_geography_is_rejected_without_mutating_input(sample: DemographicPack) -> None:
    geography = {"wrong-key": sample.regions["asia"].model_dump()}
    before = deepcopy(geography)
    with pytest.raises(ValueError, match="differs from id"):
        parse_pack(sample.metadata, geography, {"jpn": {"female": ["Yuki"], "surname": ["Sato"]}})
    assert geography == before


def test_duplicate_pool_entries_and_unicode_are_not_normalized(sample: DemographicPack) -> None:
    names = {"unicode_witness": {"female": ["Éva", "Éva", "李"], "surname": ["de Vries"]}}
    parsed = parse_pack(sample.metadata, {"asia": sample.regions["asia"].model_dump()}, names)
    assert parsed.names["unicode_witness"]["female"].given.pool.candidates == ["Éva", "Éva", "李"]
    assert parsed.names["unicode_witness"]["female"].family.pool.candidates == ["de Vries"]


def test_conflicting_definition_fails_instead_of_overwriting(sample: DemographicPack) -> None:
    register_pack(sample)
    original = NameBank.get_instance("fra")
    sample.names["fra"]["female"] = NameForm(
        given=NamePart(pool=NamePool(candidates=["Changed"])),
    )
    with pytest.raises(ValueError, match="Conflicting NameBank.*fra"):
        register_pack(sample)
    assert NameBank.get_instance("fra") is original
    assert original.forms["female"].given.pool.candidates == ["Marie", "Sophie", "Camille"]


def test_optional_full_pack_is_valid_or_truly_unavailable() -> None:
    try:
        pack = load_pack("full")
    except PackUnavailableError as exc:
        pytest.skip(str(exc))
    assert pack.metadata.label == "full"
    assert len(pack.names) > 2
    # Audit real coverage instead of xfail-ing selected countries or fabricating banks.
    assert all(country in {c.id for r in pack.regions.values() for c in r.countries.values()}
               for country, _subtype in pack.uncovered_subtypes())
