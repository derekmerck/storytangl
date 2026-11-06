"""The world-owned Afreet subset uses the shared media catalog."""
from hashlib import sha256
import json
from pathlib import Path

from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.story import Action
from tangl.vm import Ledger

ROOT = Path(__file__).resolve().parents[3] / "worlds" / "modiste_demo"


def test_world_pack_admits_and_indexes_selected_source(monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from modiste_demo.domain import load_pack, parse_annotation

    source = ROOT / "resources" / "afreet-subset.svg"
    original = source.read_bytes()
    world = WorldCompiler().compile(WorldBundle.load(ROOT))
    graph = world.create_story("modiste-catalogue").graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    assert next(edge for edge in ledger.cursor.edges_out() if isinstance(edge, Action)).text == (
        "Select underwear"
    )
    pack, catalog = load_pack(world.resources)
    again_pack, again = load_pack(world.resources)
    assert catalog.diagnostics == ()
    assert catalog.digest == again.digest and pack == again_pack
    assert source.read_bytes() == original
    assert world.resources.get_rit("afreet-subset.svg") is not None
    assert catalog.view_box == (0, 0, 496, 665)
    assert set(pack.collections["outfit"]) == {"underwear", "camisole"}
    assert set(pack.collections["body"]) == {"common"}
    assert set(pack.collections["hair"]) == {"toulouse"}
    assert set(pack.palettes) == {"rose", "blue"}
    assert pack.palettes["rose"]["skin"]["fill"] == "#FCE1D5"
    assert catalog.lookup("body.bottom").source_id == "bottom_2_"
    assert catalog.lookup("body.bottom").registration == catalog.view_box
    assert ("body_1_", "bottom_2_") in catalog.source_groups
    assert "skin" in catalog.lookup("body.bottom").channels
    assert catalog.lookup("top.camisole").channels == ("primary", "secondary", "trim")
    assert pack.coverage["unsupported_morphologies"]
    name, channel, hints, extra = parse_annotation(
        "shorts_primary_opacity:0.7", frozenset(pack.channels)
    )
    assert (name, channel, hints, extra) == ("shorts", ("primary",), {"opacity": "0.7"}, ())
    provenance = json.loads((ROOT / "resources" / "provenance.json").read_text())
    assert provenance["subset_sha256"] == sha256(original).hexdigest()
    assert provenance["source_sha256"] == (
        "3bab82e9077895b325c3e33c154e44a373e1d70a10eab7fdc68299d99ccb52ad"
    )


def test_independent_packs_with_same_alias_do_not_cross_bind(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from modiste_demo.domain import load_pack

    first_pack, first = load_pack(ResourceManager(ROOT / "resources", label="first"))
    other = tmp_path / "resources"
    other.mkdir()
    for name in ("catalog.yaml", "palettes.yaml", "afreet-subset.svg"):
        (other / name).write_bytes((ROOT / "resources" / name).read_bytes())
    svg = other / "afreet-subset.svg"
    svg.write_bytes(svg.read_bytes().replace(b'id="bottom_2_"', b'id="other_bottom"'))
    manifest = other / "catalog.yaml"
    manifest.write_text(manifest.read_text().replace("id: bottom_2_", "id: other_bottom"))
    second_pack, second = load_pack(ResourceManager(other, label="second"))
    assert not first.diagnostics and not second.diagnostics
    assert first.lookup("body.bottom").source_id == "bottom_2_"
    assert second.lookup("body.bottom").source_id == "other_bottom"
    assert first.lookup("body.bottom").source_id == "bottom_2_"
    assert first.source_sha256 != second.source_sha256
    assert first_pack.coverage == second_pack.coverage


def test_missing_world_collection_group_is_an_integrity_diagnostic(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from modiste_demo.domain import load_pack

    other = tmp_path / "resources"
    other.mkdir()
    for name in ("catalog.yaml", "palettes.yaml", "afreet-subset.svg"):
        (other / name).write_bytes((ROOT / "resources" / name).read_bytes())
    manifest = other / "catalog.yaml"
    manifest.write_text(manifest.read_text().replace("head.hair-toulouse]", "head.missing]"))
    pack, catalog = load_pack(ResourceManager(other))
    assert pack.coverage["unsupported_morphologies"]
    assert [(d.code, d.subject, d.detail) for d in catalog.diagnostics] == [
        ("missing_collection_group", "hair.toulouse", "head.missing"),
    ]


def test_audit_accepts_svg_comments(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from modiste_demo.domain import audit

    source = tmp_path / "source.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
        '<!-- note --><g id="part"/></svg>'
    )
    audit(source)
    assert "top_groups=1" in capsys.readouterr().out


def test_world_variants_report_unavailable_geometry_without_changing_choices(monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from modiste_demo.domain import load_pack, resolve_modiste

    pack, catalog = load_pack(ResourceManager(ROOT / "resources"))
    before = pack.model_dump(), catalog.digest
    plan = resolve_modiste(pack, catalog, outfit="camisole", variants=("h",))
    assert not plan.ok and not plan.entries
    assert any(d.code == "unsupported_variant" for d in plan.diagnostics)
    assert "outfit:camisole" in plan.recipe.facts
    assert (pack.model_dump(), catalog.digest) == before


def test_region_assignments_do_not_change_beauty_plan(monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from modiste_demo.domain import load_pack, resolve_modiste

    pack, catalog = load_pack(ResourceManager(ROOT / "resources"))
    changed = pack.model_copy(update={"regions": {"other": ("body.arms",)}})
    assert resolve_modiste(pack, catalog).identity == resolve_modiste(changed, catalog).identity
