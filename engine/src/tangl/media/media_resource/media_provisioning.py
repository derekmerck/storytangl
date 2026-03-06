from __future__ import annotations

from typing import Any, Iterator
from uuid import UUID

from pydantic import ConfigDict, Field

from tangl.core import BehaviorRegistry, Priority, Record
from tangl.type_hints import UnstructuredData
from tangl.vm.provision import ProvisionOffer, ProvisionPolicy, Requirement

from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from .media_resource_registry import MediaResourceRegistry

on_provision_media = BehaviorRegistry(label="provision_media")


class MediaDependencyOffer(ProvisionOffer):
    """Compatibility offer wrapper used by media provisioning tests."""

    provider_id: UUID | None = None

    def accept(self, ctx: Any = None) -> Any:
        callback = self.callback
        if callback is None:
            return None
        try:
            return callback(_ctx=ctx)
        except TypeError:
            return callback(ctx)


class MediaProvisioner(Record):
    """Provision media dependencies from existing registry entries or inline templates."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    requirement: Requirement
    registries: list[MediaResourceRegistry] = Field(default_factory=list)

    @staticmethod
    def _requirement_identifier(requirement: Requirement) -> str | None:
        extra = requirement.__pydantic_extra__ or {}
        identifier = extra.get("has_identifier") or extra.get("identifier")
        return str(identifier) if isinstance(identifier, str) and identifier else None

    @staticmethod
    def _requirement_template(requirement: Requirement) -> UnstructuredData:
        extra = requirement.__pydantic_extra__ or {}
        template = extra.get("template")
        return template if isinstance(template, dict) else {}

    @staticmethod
    def _requirement_policy(requirement: Requirement) -> ProvisionPolicy:
        value = getattr(requirement, "provision_policy", ProvisionPolicy.ANY)
        if isinstance(value, ProvisionPolicy):
            return value
        try:
            return ProvisionPolicy(value)
        except Exception:
            return ProvisionPolicy.ANY

    def _resolve_existing(self, requirement: Requirement) -> MediaRIT | None:
        identifier = self._requirement_identifier(requirement)
        for registry in self.registries:
            if identifier:
                existing = registry.find_one(has_identifier=identifier)
                if existing is not None:
                    return existing
        return None

    def _resolve_create(self, provider_template: UnstructuredData) -> MediaRIT:
        if "data" not in provider_template:
            raise ValueError("Media CREATE requires template.data")
        provider = MediaRIT(data=provider_template["data"])
        if self.registries:
            self.registries[0].add(provider)
        return provider

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        policy = self._requirement_policy(requirement)
        if not (policy & ProvisionPolicy.ANY):
            return

        existing = self._resolve_existing(requirement)
        if existing is not None and (policy & ProvisionPolicy.EXISTING):
            yield MediaDependencyOffer(
                origin_id=self.uid,
                policy=ProvisionPolicy.EXISTING,
                callback=lambda *_, _existing=existing, **__: _existing,
                priority=Priority.NORMAL,
                distance_from_caller=0,
                candidate=existing,
                provider_id=existing.uid,
            )
            return

        template = self._requirement_template(requirement)
        if template and (policy & ProvisionPolicy.CREATE):
            yield MediaDependencyOffer(
                origin_id=self.uid,
                policy=ProvisionPolicy.CREATE,
                callback=lambda *_, _templ=template, **__: self._resolve_create(_templ),
                priority=Priority.LATE,
                distance_from_caller=1,
            )

    def generate_offers(self, *, ctx: Any = None) -> list[ProvisionOffer]:
        _ = ctx
        return list(self.get_dependency_offers(self.requirement))
