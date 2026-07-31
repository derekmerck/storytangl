"""Deterministic local DiceBear portraits through the ordinary media lifecycle."""

from __future__ import annotations

from pathlib import Path

from lxml import etree
import pytest

from tangl.mechanics.presence.look import LookMediaPayload, portrait_spec_from_look
from tangl.media.media_creators.dicebear_forge import DiceBearForge, DiceBearSpec
from tangl.media.media_creators.portrait_spec import PortraitSpec
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.story.fabula import World


def _portrait_request(**overrides: object) -> PortraitSpec:
    payload: dict[str, object] = {
        "label": "portrait",
        "media_role": "avatar_im",
        "identity_key": "subject-17",
        "description": "a blonde-haired person with blue eyes",
        "traits": {
            "hair_color": "blonde",
            "eye_color": "blue",
            "skin_tone": "light",
            "hair_style": "bob",
            "body_phenotype": "fit",
        },
    }
    payload.update(overrides)
    return PortraitSpec.model_validate(payload)


def _adapt(request: PortraitSpec) -> DiceBearSpec:
    adapted = request.adapt_spec(ctx={})
    assert isinstance(adapted, DiceBearSpec)
    return adapted


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


def _portrait_story(*, requests: list[PortraitSpec]) -> dict[str, object]:
    return {
        "label": "dicebear_world",
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Generated portraits",
                        "media": [
                            {
                                "spec": {
                                    "kind": "portrait",
                                    **request.normalized_spec_payload(),
                                },
                                "media_role": "avatar_im",
                            }
                            for request in requests
                        ],
                    }
                }
            }
        },
    }


def test_look_payload_projects_to_renderer_neutral_portrait_request() -> None:
    payload = LookMediaPayload(
        description="a blonde-haired person with blue eyes",
        traits={"hair_color": "blonde", "eye_color": "blue"},
        media_role="avatar_im",
    )

    request = portrait_spec_from_look(payload, identity_key="subject-17")

    assert request.identity_key == "subject-17"
    assert request.media_role == "avatar_im"
    assert request.traits == payload.traits
    assert not hasattr(request, "options")
    assert not hasattr(request, "style_definition_hash")


def test_portrait_adapter_maps_traits_and_preserves_ignored_provenance() -> None:
    request = _portrait_request()
    equivalent = _portrait_request()
    changed_hair = _portrait_request(
        traits={**request.traits, "hair_color": "auburn"},
    )
    changed_unsupported = _portrait_request(
        traits={**request.traits, "body_phenotype": "round"},
    )
    absent = _portrait_request(traits={"hair_color": "blonde"})

    adapted = _adapt(request)

    assert adapted.options["hairColor"] == ["f5d76e"]
    assert adapted.options["eyesColor"] == ["4d8fc3"]
    assert adapted.options["skinColor"] == ["f5d6c6"]
    assert adapted.ignored_traits == {"hair_style": "bob", "body_phenotype": "fit"}
    assert adapted.seed == _adapt(equivalent).seed
    assert adapted.spec_fingerprint() == _adapt(equivalent).spec_fingerprint()
    assert adapted.spec_fingerprint() != _adapt(changed_hair).spec_fingerprint()
    assert adapted.spec_fingerprint() == _adapt(changed_unsupported).spec_fingerprint()
    assert "eyesColor" not in _adapt(absent).options
    assert "skinColor" not in _adapt(absent).options


def test_explicit_seed_and_style_definition_hash_participate_in_identity() -> None:
    explicit = _adapt(_portrait_request(explicit_seed=101))
    changed_style = explicit.model_copy(update={"style_definition_hash": "different-definition"})

    assert explicit.seed == "101"
    assert explicit.options["seed"] == "101"
    assert explicit.spec_fingerprint() != changed_style.spec_fingerprint()


def test_dicebear_forge_returns_safe_svg_and_resolved_execution_options() -> None:
    adapted = _adapt(_portrait_request())

    svg, realized = DiceBearForge().create_media(adapted)

    root = etree.fromstring(svg.encode("utf-8"))
    assert root.tag.endswith("svg")
    assert not [
        value
        for element in root.iter()
        for attribute, value in element.attrib.items()
        if attribute.endswith("href") and value.startswith(("http:", "https:"))
    ]
    assert realized.renderer_name == "dicebear-core"
    assert realized.renderer_version is not None
    assert realized.resolved_options is not None
    assert realized.resolved_options["hairColor"] == ["#f5d76e"]
    assert "hair_style" not in realized.resolved_options


def test_portraits_provision_to_one_reusable_story_rit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )
    request = _portrait_request(label="guard_portrait")
    world = World.from_script_data(
        script_data=_portrait_story(requests=[request, request.model_copy(deep=True)])
    )
    story = world.create_story("dicebear-story").graph
    block = next(node for node in story.values() if getattr(node, "label", None) == "start")
    deps = [edge for edge in block.edges_out() if isinstance(edge, MediaDep)]

    assert len(deps) == 2
    assert deps[0].provider is not None
    assert deps[0].provider.uid == deps[1].provider.uid

    provider = deps[0].provider
    assert isinstance(provider, MediaRIT)
    assert provider.path is not None and provider.path.exists()
    assert provider.content_hash
    assert provider.derivation_spec is not None
    assert provider.derivation_spec["traits"]["hair_style"] == "bob"
    assert provider.adapted_spec is not None
    assert provider.adapted_spec["ignored_traits"] == {
        "hair_style": "bob",
        "body_phenotype": "fit",
    }
    assert provider.execution_spec is not None
    assert provider.execution_spec["renderer_name"] == "dicebear-core"
    assert etree.fromstring(provider.path.read_bytes()).tag.endswith("svg")
