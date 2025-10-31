from __future__ import annotations

import copy

import pytest
from pydantic import Field

from tangl.core import Graph, Node, Registry
from tangl.vm import Frame, ResolutionPhase as P, ProvisioningPolicy
from tangl.vm.context import Context
from tangl.vm.planning import Dependency, ProvisionOffer, Provisioner, Requirement


class ActorProvisioner(Provisioner):
    """Provisioner that injects domain templates when collecting offers."""

    def __init__(self, templates: dict[str, dict]):
        super().__init__(label="actor_provisioner")
        self._templates = templates

    def get_offers(
        self,
        requirement: Requirement,
        *,
        ctx: Context | None = None,
    ) -> list[ProvisionOffer]:
        injected_template = False
        original_template = requirement.template
        template = self._templates.get(requirement.identifier)
        if template is not None and requirement.template is None:
            requirement.template = copy.deepcopy(template)
            injected_template = True
        try:
            return super().get_offers(requirement, ctx=ctx)
        finally:
            if injected_template:
                requirement.template = original_template


class ActorDomain:
    """Domain that publishes an actor provisioner seeded with templates."""

    selector_type = Node
    templates: dict[str, dict] = Field(default_factory=dict)

    def __init__(self, *, label: str, templates: dict[str, dict]):
        super().__init__(label=label, templates=templates)
        self.handlers.add(ActorProvisioner(self.templates))

@pytest.mark.xfail(rason="deprecated, provisioning in revision, domains going away")
def test_custom_provisioner_from_domain_creates_actor():
    graph = Graph(label="story")
    scene = graph.add_node(label="scene", tags={"domain:actors"})

    requirement = Requirement[Node](
        graph=graph,
        identifier="rogue",
        policy=ProvisioningPolicy.ANY,
        hard_requirement=True,
    )
    Dependency[Node](
        graph=graph,
        source_id=scene.uid,
        requirement=requirement,
        label="needs_actor",
    )

    actor_templates = {
        "rogue": {"obj_cls": Node, "label": "rogue", "tags": {"role:actor"}},
    }
    domain_registry: Registry[AffiliateDomain] = Registry(label="domains")
    domain_registry.add(ActorDomain(label="actors", templates=actor_templates))

    frame = Frame(graph=graph, cursor_id=scene.uid, domain_registries=[domain_registry])
    frame.run_phase(P.PLANNING)

    provider = requirement.provider
    assert provider is not None, "Planning should create a provider from domain template"
    assert provider.label == "rogue"
    assert provider in graph
    assert provider.has_tags({"role:actor"})
    assert list(graph.find_nodes(label="rogue")) == [provider]
