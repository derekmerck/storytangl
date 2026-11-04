"""Read-only SVG catalog indexing and integrity diagnostics."""
from pathlib import Path

from tangl.media.media_creators.svg_forge.svg_catalog import SvgGroupDeclaration, index_svg_catalog
from tangl.media.media_resource.resource_manager import ResourceManager


SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 30">
<defs><linearGradient id="shade"/><clipPath id="cut"><rect width="3" height="3"/></clipPath></defs>
<g id="body_original"><path fill="url(#shade)" clip-path="url(#cut)" d="M0 0h1v1z"/></g>
<g id="dress_original"><use href="#body_original"/></g></svg>'''


def admitted(path: Path, data: bytes = SVG):
    path.mkdir(parents=True, exist_ok=True)
    (path / "source.svg").write_bytes(data)
    manager = ResourceManager(path)
    return manager, manager.register_file(Path("source.svg"))


def test_index_preserves_source_references_order_channels_and_digest(tmp_path: Path) -> None:
    manager, source = admitted(tmp_path)
    original = source.path.read_bytes()
    declarations = (
        SvgGroupDeclaration(key="figure.body", source_id="body_original", aliases=("body",),
                            order=2, channels=("complexion",), registration=(0, 0, 20, 30)),
        SvgGroupDeclaration(key="figure.dress", source_id="dress_original", order=5),
    )
    palettes = {"day": {"complexion": {"fill": "#abc"}}}
    before = repr((declarations, palettes))
    catalog = index_svg_catalog(source, declarations, channels=frozenset({"complexion"}),
                                palettes=palettes)
    again = index_svg_catalog(source, declarations, channels=frozenset({"complexion"}),
                              palettes=palettes)
    assert not catalog.diagnostics
    assert catalog.digest == again.digest and repr((declarations, palettes)) == before
    assert source.path.read_bytes() == original
    assert manager.get_rit("source.svg") is source
    assert catalog.source_label == "source.svg"
    assert catalog.resource_hash == source.content_hash.hex()
    assert catalog.view_box == (0, 0, 20, 30)
    assert [entry.order for entry in catalog.entries] == [2, 5]
    assert catalog.lookup("body").locator == "#body_original"
    assert catalog.lookup("body").channels == ("complexion",)
    assert catalog.lookup("unknown") is None
    changed = index_svg_catalog(source, declarations, channels=frozenset({"complexion"}),
                                palettes={"day": {"complexion": {"fill": "#def"}}})
    assert changed.digest != catalog.digest


def test_diagnostics_are_deterministic_and_keep_missing_groups_explicit(tmp_path: Path) -> None:
    bad = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 30">
      <g id="item"/><g id="item"/><path fill="url(#missing-gradient)"/>
      <path clip-path="url(#missing-clip)"/><use href="#missing-href"/></svg>'''
    _, source = admitted(tmp_path, bad)
    requests = (
        SvgGroupDeclaration(key="one", source_id="item", aliases=("same",)),
        SvgGroupDeclaration(key="two", source_id="absent", aliases=("same",)),
        SvgGroupDeclaration(key="three", source_id="item", channels=("unknown",),
                            registration=(0, 0, 21, 30)),
    )
    result = index_svg_catalog(source, requests, channels=frozenset({"ink"}), palettes={
        "bad-color": {"ink": {"fill": "not-a-color"}},
        "unknown-channel": {"other": {"fill": "red"}},
        "empty": {"ink": {}},
    })
    codes = {d.code for d in result.diagnostics}
    assert {
        "duplicate_id", "ambiguous_group", "missing_group", "key_collision",
        "unresolved_reference", "undeclared_palette_channel", "malformed_palette_binding",
    } <= codes
    assert {d.subject for d in result.diagnostics if d.code == "unresolved_reference"} == {
        "missing-gradient", "missing-clip", "missing-href",
    }
    assert result.entries == ()
    assert result.diagnostics == index_svg_catalog(source, requests, channels=frozenset({"ink"}),
        palettes={"bad-color": {"ink": {"fill": "not-a-color"}},
                  "unknown-channel": {"other": {"fill": "red"}}, "empty": {"ink": {}}}).diagnostics


def test_channel_and_registration_mismatch_are_independent_diagnostics(tmp_path: Path) -> None:
    _, source = admitted(tmp_path)
    request = SvgGroupDeclaration(key="body", source_id="body_original", channels=("unknown",),
                                  registration=(0, 0, 21, 30))
    catalog = index_svg_catalog(source, (request,), channels=frozenset({"ink"}))
    assert {d.code for d in catalog.diagnostics} == {"registration_mismatch", "undeclared_channel"}
    assert catalog.lookup("body").source_id == "body_original"


def test_separate_resource_managers_keep_competing_aliases_local(tmp_path: Path) -> None:
    _, first = admitted(tmp_path / "a")
    _, second = admitted(tmp_path / "b", SVG.replace(b'body_original', b'other_body'))
    a = index_svg_catalog(first, (SvgGroupDeclaration(key="body", source_id="body_original"),))
    b = index_svg_catalog(second, (SvgGroupDeclaration(key="body", source_id="other_body"),))
    assert a.lookup("body").locator == "#body_original"
    assert b.lookup("body").locator == "#other_body"
    assert a.source_sha256 != b.source_sha256 and a.digest != b.digest


def test_invalid_viewbox_palette_reference_and_changed_source_are_reported(tmp_path: Path) -> None:
    _, source = admitted(tmp_path)
    source.path.write_bytes(SVG.replace(b'viewBox="0 0 20 30"', b'viewBox="0 0 0 30"'))
    catalog = index_svg_catalog(
        source,
        (SvgGroupDeclaration(key="body", source_id="body_original"),),
        channels=frozenset({"ink"}),
        palettes={"day": {"ink": {"fill": "url(#missing-paint)"}}},
    )
    assert {d.code for d in catalog.diagnostics} == {
        "invalid_viewbox", "resource_hash_mismatch", "unresolved_reference",
    }
    assert catalog.view_box is None


def test_malformed_palette_shapes_produce_diagnostics(tmp_path: Path) -> None:
    _, source = admitted(tmp_path)
    catalog = index_svg_catalog(source, (), channels=frozenset({"ink"}), palettes={
        "bad": {"ink": {"opacity": "2"}, 12: {"fill": "red"}},
        "wrong": ["not", "a", "mapping"],
    })
    assert {d.code for d in catalog.diagnostics} == {
        "malformed_palette", "malformed_palette_binding",
    }
