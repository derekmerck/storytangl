"""Contract tests for ``tangl.vm38.provision.requirement``.

Organized by concept:
- Requirement: satisfaction, matching, policy
- HasRequirement: provider linking
- Dependency: pull-resource edge, provider syncs successor
- Affordance: push-resource edge, provider syncs successor
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.core38 import Entity, Graph, Registry, RegistryAware, Selector
from tangl.vm38.provision import (
    Affordance,
    Dependency,
    HasRequirement,
    ProvisionPolicy,
    Requirement,
)


# ============================================================================
# Requirement
# ============================================================================


class TestRequirementSatisfaction:
    def test_unsatisfied_by_default(self) -> None:
        req = Requirement(has_identifier="foo")
        assert not req.satisfied

    def test_satisfied_when_provider_set(self) -> None:
        req = Requirement(has_identifier="foo")
        from uuid import uuid4
        req.provider_id = uuid4()
        assert req.satisfied

    def test_soft_requirement_satisfied_without_provider(self) -> None:
        req = Requirement(hard_requirement=False)
        assert req.satisfied

    def test_satisfied_by_matching_entity(self) -> None:
        e = Entity(label="foo")
        req = Requirement.from_identifier("foo")
        assert req.satisfied_by(e)

    def test_not_satisfied_by_non_matching(self) -> None:
        e = Entity(label="bar")
        req = Requirement.from_identifier("foo")
        assert not req.satisfied_by(e)


class TestRequirementPolicy:
    def test_default_policy_is_any(self) -> None:
        req = Requirement(has_identifier="foo")
        assert req.provision_policy == ProvisionPolicy.ANY

    def test_custom_policy(self) -> None:
        req = Requirement(
            has_identifier="foo",
            provision_policy=ProvisionPolicy.EXISTING,
        )
        assert req.provision_policy == ProvisionPolicy.EXISTING


# ============================================================================
# HasRequirement
# ============================================================================


class TestHasRequirement:
    def test_provider_set_and_get(self) -> None:
        reg = Registry()
        carrier = HasRequirement(requirement=Requirement(has_identifier="foo"))
        reg.add(carrier)
        provider = RegistryAware(label="foo")
        reg.add(provider)

        carrier.provider = provider
        assert carrier.satisfied
        assert carrier.provider is provider

    def test_provider_mismatch_raises(self) -> None:
        reg = Registry()
        carrier = HasRequirement(requirement=Requirement(has_identifier="foo"))
        reg.add(carrier)
        wrong = RegistryAware(label="bar")
        reg.add(wrong)

        with pytest.raises(ValueError, match="not satisfied"):
            carrier.provider = wrong

    def test_provider_sets_resolution_metadata_from_ctx(self) -> None:
        reg = Registry()
        carrier = HasRequirement(requirement=Requirement(has_identifier="foo"))
        reg.add(carrier)
        provider = RegistryAware(label="foo")
        reg.add(provider)
        ctx = SimpleNamespace(step=7, cursor_id=provider.uid)

        carrier.set_provider(provider, _ctx=ctx)
        assert carrier.requirement.resolved_step == 7
        assert carrier.requirement.resolved_cursor_id == provider.uid

    def test_resolution_reason_and_meta_delegate_from_requirement(self) -> None:
        reg = Registry()
        carrier = HasRequirement(requirement=Requirement(has_identifier="foo"))
        reg.add(carrier)
        carrier.requirement.resolution_reason = "no_offers"
        carrier.requirement.resolution_meta = {"alternatives": []}
        assert carrier.resolution_reason == "no_offers"
        assert carrier.resolution_meta == {"alternatives": []}


# ============================================================================
# Dependency — pull resource
# ============================================================================


class TestDependency:
    def test_unsatisfied_on_creation(self) -> None:
        reg = Registry()
        dep = Dependency(requirement=Requirement(has_identifier="foo"))
        reg.add(dep)
        assert not dep.satisfied

    def test_set_provider_syncs_successor(self) -> None:
        reg = Registry()
        dep = Dependency(requirement=Requirement(has_identifier="foo"))
        reg.add(dep)
        provider = RegistryAware(label="foo")
        reg.add(provider)

        dep.set_provider(provider)
        assert dep.satisfied
        assert dep.provider is provider
        assert dep.successor is provider

    def test_set_successor_syncs_provider(self) -> None:
        reg = Registry()
        dep = Dependency(requirement=Requirement(has_identifier="foo"))
        reg.add(dep)
        provider = RegistryAware(label="foo")
        reg.add(provider)

        dep.set_successor(provider)
        assert dep.satisfied
        assert dep.provider is provider


# ============================================================================
# Affordance — push resource
# ============================================================================


class TestAffordance:
    def test_unsatisfied_on_creation(self) -> None:
        reg = Registry()
        aff = Affordance(requirement=Requirement(has_identifier="foo"))
        reg.add(aff)
        assert not aff.satisfied

    def test_set_provider_syncs_successor(self) -> None:
        reg = Registry()
        aff = Affordance(requirement=Requirement(has_identifier="foo"))
        reg.add(aff)
        provider = RegistryAware(label="foo")
        reg.add(provider)

        aff.set_provider(provider)
        assert aff.satisfied
        assert aff.provider is provider
        assert aff.successor is provider

    def test_set_successor_syncs_provider(self) -> None:
        reg = Registry()
        aff = Affordance(requirement=Requirement(has_identifier="foo"))
        reg.add(aff)
        provider = RegistryAware(label="foo")
        reg.add(provider)

        aff.set_successor(provider)
        assert aff.satisfied
        assert aff.provider is provider

    def test_set_predecessor_does_not_bind_provider(self) -> None:
        reg = Registry()
        aff = Affordance(requirement=Requirement(has_identifier="foo"))
        reg.add(aff)
        frontier = RegistryAware(label="frontier")
        reg.add(frontier)

        aff.set_predecessor(frontier)
        assert aff.predecessor is frontier
        assert aff.provider is None
        assert not aff.satisfied
