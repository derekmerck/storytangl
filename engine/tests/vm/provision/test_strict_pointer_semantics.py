"""Tests for strict pointer semantics in provisioning lookups.

Organized by functionality:
- Qualified identifiers: no tail fallback when resolving templates.
- Unqualified identifiers: label lookup still works.
"""

from __future__ import annotations

from tangl.core.factory import Template, TemplateFactory
from tangl.core.graph import Graph, Node
from tangl.vm.provision import ProvisioningContext, ProvisioningPolicy, Requirement
from tangl.vm.provision.provisioner import TemplateProvisioner


# ============================================================================
# Qualified identifiers
# ============================================================================

class TestQualifiedIdentifierLookup:
    """Tests for qualified identifier lookup behavior."""

    def test_qualified_ref_no_tail_fallback(self) -> None:
        """Qualified refs should not fallback to tail labels."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")
        factory.add(Template(label="shop", obj_cls=Node))

        requirement = Requirement(
            graph=graph,
            template_ref="book1.shop",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )
        provisioner = TemplateProvisioner(factory=factory)
        ctx = ProvisioningContext(graph=graph, step=0)

        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

        assert offers == []


class TestUnqualifiedIdentifierLookup:
    """Tests for unqualified identifier lookup behavior."""

    def test_unqualified_ref_uses_label_lookup(self) -> None:
        """Unqualified refs should resolve via label lookup."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")
        factory.add(Template(label="shop", obj_cls=Node))

        requirement = Requirement(
            graph=graph,
            template_ref="shop",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )
        provisioner = TemplateProvisioner(factory=factory)
        ctx = ProvisioningContext(graph=graph, step=0)

        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

        assert len(offers) == 1
