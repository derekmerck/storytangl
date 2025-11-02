from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.core.graph import Graph, Node
from tangl.vm.provision.offer import ProvisionOffer
from tangl.vm.provision.provisioner import Provisioner
from tangl.vm.provision.requirement import Requirement, ProvisioningPolicy


@pytest.fixture
def provisioner() -> Provisioner:
    return Provisioner()


def _make_requirement(policy: ProvisioningPolicy, **kwargs) -> Requirement:
    graph = kwargs.pop("graph", None)
    if graph is None:
        graph = Graph()
    return Requirement(graph=graph, policy=policy, **kwargs)


def test_iter_requirement_registries_includes_requirement_graph(provisioner: Provisioner) -> None:
    req_graph = Graph()
    requirement = _make_requirement(
        ProvisioningPolicy.EXISTING,
        identifier="npc-1",
        graph=req_graph,
    )

    registries = provisioner.iter_requirement_registries(requirement)

    assert registries == (req_graph,)


def test_iter_requirement_registries_injects_context_graph(provisioner: Provisioner) -> None:
    requirement_graph = Graph()
    ctx_graph = Graph()
    requirement = _make_requirement(
        ProvisioningPolicy.EXISTING,
        identifier="npc-2",
        graph=requirement_graph,
    )
    ctx = SimpleNamespace(graph=ctx_graph)

    registries = provisioner.iter_requirement_registries(requirement, ctx=ctx)

    assert registries == (ctx_graph, requirement_graph)


def test_iter_requirement_registries_avoids_duplicate_context(provisioner: Provisioner) -> None:
    shared_graph = Graph()
    requirement = _make_requirement(
        ProvisioningPolicy.EXISTING,
        identifier="npc-3",
        graph=shared_graph,
    )
    ctx = SimpleNamespace(graph=shared_graph)

    registries = provisioner.iter_requirement_registries(requirement, ctx=ctx)

    assert registries == (shared_graph,)


def test_resolve_delegates_to_dependency_offers_for_existing(monkeypatch, provisioner: Provisioner) -> None:
    requirement = _make_requirement(
        ProvisioningPolicy.EXISTING,
        identifier="npc-4",
    )
    provider_graph = Graph()
    provider = Node(graph=provider_graph)

    offer = ProvisionOffer(
        requirement=requirement,
        provisioner=provisioner,
        operation=ProvisioningPolicy.EXISTING,
        accept_func=lambda: provider,
    )

    captured: list[tuple[Requirement, object | None]] = []

    def fake_get_dependency_offers(self: Provisioner, req: Requirement, *, ctx=None):
        captured.append((req, ctx))
        return [offer]

    monkeypatch.setattr(Provisioner, "get_dependency_offers", fake_get_dependency_offers)

    with pytest.warns(DeprecationWarning):
        resolved = provisioner.resolve(requirement)

    assert resolved is provider
    assert captured == [(requirement, None)]


def test_resolve_prefers_matching_policy_for_create(monkeypatch, provisioner: Provisioner) -> None:
    requirement = _make_requirement(
        ProvisioningPolicy.CREATE,
        template={"label": "new-provider"},
    )
    provider_graph = Graph()
    fallback_provider = Node(graph=provider_graph)
    create_graph = Graph()
    created_provider = Node(graph=create_graph)

    existing_offer = ProvisionOffer(
        requirement=requirement,
        provisioner=provisioner,
        operation=ProvisioningPolicy.EXISTING,
        accept_func=lambda: fallback_provider,
    )
    create_offer = ProvisionOffer(
        requirement=requirement,
        provisioner=provisioner,
        operation=ProvisioningPolicy.CREATE,
        accept_func=lambda: created_provider,
    )

    monkeypatch.setattr(
        Provisioner,
        "get_dependency_offers",
        lambda self, req, *, ctx=None: [existing_offer, create_offer],
    )

    with pytest.warns(DeprecationWarning):
        resolved = provisioner.resolve(requirement)

    assert resolved is created_provider
