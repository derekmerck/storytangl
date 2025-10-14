from __future__ import annotations

from pathlib import Path

import pytest

from tangl.media.media_dependency import MediaDependency, MediaRequirement
from tangl.vm.planning import ProvisioningPolicy


def test_build_requirement_from_static_path(tmp_path: Path) -> None:
    path = tmp_path / "forest-dawn.png"
    path.write_bytes(b"image-data")

    dependency = MediaDependency(
        static_path=path,
        role="background",
        staging_hint="inline",
    )

    requirement = dependency.build_requirement()

    assert isinstance(requirement, MediaRequirement)
    assert requirement.policy is ProvisioningPolicy.EXISTING
    assert requirement.criteria == {"path": path}
    assert requirement.role == "background"
    assert requirement.staging_hint == "inline"


def test_build_requirement_from_tags() -> None:
    dependency = MediaDependency(
        discovery_tags={"forest", "dawn"},
        discovery_criteria={"media_type": "image"},
        role="background",
    )

    requirement = dependency.build_requirement()

    assert requirement.criteria["tags"] == {"forest", "dawn"}
    assert requirement.criteria["media_type"] == "image"
    assert requirement.role == "background"


def test_callable_tags_require_context() -> None:
    dependency = MediaDependency(discovery_tags=lambda ctx: {ctx})

    with pytest.raises(ValueError):
        dependency.build_requirement()

    requirement = dependency.build_requirement(context="forest")
    assert requirement.criteria["tags"] == {"forest"}


def test_build_requirement_requires_strategy() -> None:
    dependency = MediaDependency()

    with pytest.raises(ValueError):
        dependency.build_requirement()
