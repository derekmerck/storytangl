from __future__ import annotations

"""Media dependency edges and requirements."""

from collections.abc import Callable, Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from tangl.media.media_resource_inventory_tag import MediaResourceInventoryTag
from tangl.type_hints import StringMap, Tag
from tangl.vm.planning import Dependency, ProvisioningPolicy, Requirement


class MediaRequirement(Requirement[MediaResourceInventoryTag]):
    """MediaRequirement(identifier | criteria | template, policy, *, role=None, staging_hint=None)

    Requirement specialised for media resources.

    Why
    ---
    Media edges frequently need to attach presentation hints (role, staging) in
    addition to the underlying discovery criteria.  The
    :class:`MediaRequirement` keeps these annotations co-located with the
    :class:`~tangl.media.media_resource_inventory_tag.MediaResourceInventoryTag`
    criteria used during provisioning.

    Key Features
    ------------
    * **Role metadata** – exposes ``role`` so downstream planners can map the
      media to a narrative slot (e.g. ``background``).
    * **Staging hints** – optional ``staging_hint`` guides later URL or inline
      dereferencing.

    API
    ---
    - :attr:`role`
    - :attr:`staging_hint`
    """

    role: str | None = None
    staging_hint: str | None = None


class MediaDependency(Dependency[MediaResourceInventoryTag]):
    """MediaDependency(source, requirement, *, static_path=None, discovery_tags=None)

    Dependency edge that resolves to a media inventory tag.

    Why
    ---
    Narrative nodes frequently request media assets either by explicit path or
    by semantic tags.  :class:`MediaDependency` captures those strategies and
    provides a helper to turn them into a :class:`MediaRequirement` during
    planning.

    Key Features
    ------------
    * **Dual strategies** – supports direct ``static_path`` lookups and
      discovery via ``discovery_tags``/``discovery_criteria``.
    * **Metadata bridging** – carries ``role`` and ``staging_hint`` through to
      the generated requirement.
    * **Handler ready** – stores the resolved ``successor_id`` for later
      dereferencing (Phase 5 will hydrate this from context registries).

    API
    ---
    - :meth:`build_requirement`
    - :attr:`successor_id`
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    requirement: MediaRequirement = Field(default_factory=MediaRequirement)
    static_path: Path | None = None
    discovery_tags: set[Tag] | Tag | Callable[[Any], Iterable[Tag] | Tag] | None = None
    discovery_criteria: StringMap | None = None
    role: str | None = None
    staging_hint: str | None = None
    successor_id: UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_path(cls, data: dict[str, Any]) -> dict[str, Any]:
        static_path = data.get("static_path")
        if static_path is not None and not isinstance(static_path, Path):
            data = dict(data)
            data["static_path"] = Path(static_path)
        return data

    def _resolve_discovery_tags(self, context: Any | None) -> set[Tag]:
        tags = self.discovery_tags
        if callable(tags):
            if context is None:
                raise ValueError("Callable discovery_tags requires a context")
            resolved = tags(context)
            if isinstance(resolved, (str, bytes)):
                return {resolved}
            if isinstance(resolved, Iterable):
                return set(resolved)
            return {resolved}
        if tags is None:
            return set()
        if isinstance(tags, set):
            return set(tags)
        if isinstance(tags, (str, bytes)):
            return {tags}
        if isinstance(tags, Iterable):
            return set(tags)
        return {tags}

    def build_requirement(self, context: Any | None = None) -> MediaRequirement:
        """Construct a :class:`MediaRequirement` for the dependency."""

        if self.static_path is not None:
            resolved = self.static_path.expanduser()
            requirement = MediaRequirement(
                criteria={"path": resolved},
                policy=ProvisioningPolicy.EXISTING,
                role=self.role,
                staging_hint=self.staging_hint,
            )
            requirement.graph = self.graph
            self.requirement = requirement
            return requirement

        tags = self._resolve_discovery_tags(context)
        if tags or self.discovery_criteria:
            criteria: StringMap = {}
            if self.discovery_criteria:
                criteria = deepcopy(self.discovery_criteria)
            if tags:
                criteria["tags"] = tags
            requirement = MediaRequirement(
                criteria=criteria,
                policy=ProvisioningPolicy.EXISTING,
                role=self.role,
                staging_hint=self.staging_hint,
            )
            requirement.graph = self.graph
            self.requirement = requirement
            return requirement

        raise ValueError("MediaDependency requires a static_path or discovery criteria")

    @property
    def successor(self) -> Optional[MediaResourceInventoryTag]:
        """Placeholder accessor for resolved media (Phase 5 will hydrate)."""

        return None
