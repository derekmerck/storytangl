from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable
from uuid import UUID

from tangl.core import Selector, TemplateRegistry


ScopeProvider = Callable[..., Iterable[Iterable[Any]]]


@dataclass(slots=True)
class ScriptManager:
    """Runtime template lookup and scope-group facade for story."""

    template_registry: TemplateRegistry
    world_scope_provider: ScopeProvider | None = None

    def find_template(self, reference: str | UUID | Selector | None) -> Any | None:
        """Resolve one template by selector, uid, identifier, or label."""
        if reference is None:
            return None
        if isinstance(reference, Selector):
            return self.template_registry.find_one(reference)
        if isinstance(reference, UUID):
            return self.template_registry.get(reference)

        key = str(reference)
        found = self.template_registry.find_one(Selector(has_identifier=key))
        if found is not None:
            return found
        return self.template_registry.find_one(Selector(label=key))

    def find_templates(self, selector: Selector | None = None) -> list[Any]:
        """Return templates matching selector, or all templates when omitted."""
        if selector is None:
            return list(self.template_registry.values())
        return list(selector.filter(self.template_registry.values()))

    def get_template_scope_groups(
        self,
        *,
        caller: Any,
        graph: Any = None,
        lineage_ids: Iterable[UUID] = (),
    ) -> list[list[Any]]:
        """Return template groups ordered from nearest scope to broadest scope."""
        groups: list[list[Any]] = []
        seen_ids: set[UUID] = set()

        def _add_group(values: Iterable[Any]) -> None:
            bucket: list[Any] = []
            for value in values:
                uid = getattr(value, "uid", None)
                if uid is None or uid in seen_ids:
                    continue
                seen_ids.add(uid)
                bucket.append(value)
            if bucket:
                groups.append(bucket)

        for template_id in lineage_ids:
            template = self.template_registry.get(template_id)
            if template is None:
                continue
            values: list[Any] = [template]
            members = getattr(template, "members", None)
            if callable(members):
                values.extend(list(members()))
            _add_group(values)

        _add_group(self.template_registry.values())

        if callable(self.world_scope_provider):
            world_groups = self.world_scope_provider(caller=caller, graph=graph) or ()
            for group in world_groups:
                _add_group(group)

        return groups
