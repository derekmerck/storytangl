"""Offline coverage for the ComfyUI helper.

No worker, no models, no GPU, no network. Live rendering is opt-in and lives
elsewhere; nothing here may become live merely because a worker is configured.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from tangl.media.media_creators.comfy_forge._common import configured_comfy_url

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_TEMPLATES = REPO_ROOT / "scripts" / "examples" / "comfy"


def _templates() -> list[Path]:
    return sorted(EXAMPLE_TEMPLATES.glob("*.json.j2"))


# ── template rendering ───────────────────────────────────────────────────

@pytest.mark.parametrize("template", _templates(), ids=lambda p: p.name)
def test_templates_render_to_valid_api_json(template: Path, tmp_path: Path) -> None:
    """Every bundled template renders to an API-shaped graph offline."""

    from comfy_batch import TEMPLATES

    params = {
        "prompt": 'a "quoted" prompt\nwith newline',
        "width": 512,
        "height": 320,
        "steps": 4,
        "cfg": 1,
        "seed": 7,
        "denoise": 0.9,
        "prefix": "test",
        "color": 3368652,
        "images": {"source": "src.png", "reference": "ref.png"},
    }
    rendered = TEMPLATES.from_string(template.read_text()).render(**params)
    workflow = json.loads(rendered)

    assert workflow, f"{template.name} rendered an empty graph"
    for node_id, node in workflow.items():
        assert "class_type" in node, f"{template.name}:{node_id} has no class_type"
        assert isinstance(node.get("inputs", {}), dict)


@pytest.mark.parametrize("template", _templates(), ids=lambda p: p.name)
def test_template_wires_have_no_dangling_references(template: Path) -> None:
    """Every ["node", index] wire must name a node present in the graph."""

    from comfy_batch import TEMPLATES

    rendered = TEMPLATES.from_string(template.read_text()).render(
        prompt="p", width=512, height=320, steps=4, cfg=1, seed=1,
        denoise=0.9, prefix="t", color=0, images={"source": "s.png", "reference": "r.png"},
    )
    workflow = json.loads(rendered)
    for node_id, node in workflow.items():
        for name, value in node.get("inputs", {}).items():
            if isinstance(value, list) and value and isinstance(value[0], str):
                assert value[0] in workflow, (
                    f"{template.name}:{node_id}.{name} wires to missing node {value[0]!r}"
                )


def test_prompt_quoting_survives_tojson() -> None:
    """`| tojson` must make quotes and newlines safe without manual escaping."""

    from comfy_batch import TEMPLATES

    nasty = 'he said "no"\nand \\ left'
    rendered = TEMPLATES.from_string('{"t": {{ prompt | tojson }}}').render(prompt=nasty)
    assert json.loads(rendered)["t"] == nasty


# ── settings-driven endpoint selection ───────────────────────────────────

def test_url_default_prefers_configured_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("comfy_batch.configured_comfy_url", lambda: "http://worker:8188")
    from comfy_batch import build_parser

    args = build_parser().parse_args(["submit", "w.j2", "--receipts", "r.json"])
    assert args.url == "http://worker:8188"


def test_url_default_falls_back_to_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("comfy_batch.configured_comfy_url", lambda: None)
    from comfy_batch import build_parser

    args = build_parser().parse_args(["submit", "w.j2", "--receipts", "r.json"])
    assert args.url == "http://127.0.0.1:8188"


def test_explicit_url_overrides_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("comfy_batch.configured_comfy_url", lambda: "http://worker:8188")
    from comfy_batch import build_parser

    args = build_parser().parse_args(
        ["submit", "w.j2", "--receipts", "r.json", "--url", "http://other:9000"]
    )
    assert args.url == "http://other:9000"


def test_configured_comfy_url_is_a_string_or_none() -> None:
    """The accessor is the only sanctioned source of a worker endpoint."""

    resolved = configured_comfy_url()
    assert resolved is None or isinstance(resolved, str)


# ── PNG workflow recovery ────────────────────────────────────────────────

def _png_with_metadata(path: Path, **chunks: str) -> Path:
    info = PngImagePlugin.PngInfo()
    for key, value in chunks.items():
        info.add_text(key, value)
    Image.new("RGB", (4, 4), (0, 0, 0)).save(path, pnginfo=info)
    return path


def test_workflow_recovered_from_png_metadata(tmp_path: Path) -> None:
    from workflow_from_png import extract, suggest

    workflow = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": "m.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": "hi", "clip": ["c", 0]}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": 11}},
    }
    png = _png_with_metadata(tmp_path / "a.png", prompt=json.dumps(workflow))

    recovered, has_layout = extract(png)
    assert recovered == workflow
    assert has_layout is False

    names = {name for _node, name, _value in suggest(recovered)}
    assert {"text", "noise_seed"} <= names
    # Wires are not literals and must never be offered as parameters.
    assert "clip" not in names


def test_ui_layout_chunk_is_reported_when_present(tmp_path: Path) -> None:
    from workflow_from_png import extract

    png = _png_with_metadata(
        tmp_path / "b.png", prompt=json.dumps({"n": {"class_type": "X"}}), workflow="{}"
    )
    _recovered, has_layout = extract(png)
    assert has_layout is True


def test_png_without_metadata_is_refused(tmp_path: Path) -> None:
    from workflow_from_png import extract

    plain = tmp_path / "plain.png"
    Image.new("RGB", (4, 4)).save(plain)

    with pytest.raises(SystemExit, match="no 'prompt' chunk"):
        extract(plain)
