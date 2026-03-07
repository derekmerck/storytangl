.. currentmodule:: tangl.vm

tangl.vm.provision
==================

Constraint, offer, and resolver mechanisms for satisfying frontier
dependencies.

.. rubric:: Related design docs

- :doc:`../../design/planning/PROVISIONING`
- :doc:`../../design/planning/PROVISIONING_BEHAVIOR`

.. rubric:: Related notes

- :doc:`../../notes/audits/vm38-doc-audit`
- :doc:`../../notes/reference/code_adjacent_design_docs`

Constraint types
----------------

.. autoclass:: tangl.vm.provision.requirement.Requirement
.. autoclass:: tangl.vm.provision.requirement.HasRequirement
.. autoclass:: tangl.vm.provision.requirement.Dependency
.. autoclass:: tangl.vm.provision.requirement.Affordance

Offers and provisioners
-----------------------

.. autoclass:: tangl.vm.provision.provisioner.ProvisionPolicy
.. autoclass:: tangl.vm.provision.provisioner.ProvisionOffer
.. autoclass:: tangl.vm.provision.provisioner.Provisioner
.. autoclass:: tangl.vm.provision.provisioner.FindProvisioner
.. autoclass:: tangl.vm.provision.provisioner.TemplateProvisioner
.. autoclass:: tangl.vm.provision.provisioner.TokenProvisioner
.. autoclass:: tangl.vm.provision.provisioner.InlineTemplateProvisioner
.. autoclass:: tangl.vm.provision.provisioner.StubProvisioner
.. autoclass:: tangl.vm.provision.provisioner.UpdateCloneProvisioner
.. autoclass:: tangl.vm.provision.provisioner.CloneProvisioner

Resolution
----------

.. autoclass:: tangl.vm.provision.resolver.Resolver

Selected methods
----------------

.. automethod:: tangl.vm.provision.resolver.Resolver.from_ctx
.. automethod:: tangl.vm.provision.resolver.Resolver.gather_offers
.. automethod:: tangl.vm.provision.resolver.Resolver.resolve_requirement
.. automethod:: tangl.vm.provision.resolver.Resolver.resolve_dependency
.. automethod:: tangl.vm.provision.resolver.Resolver.resolve_frontier_node
.. automethod:: tangl.vm.provision.resolver.Resolver.preview_requirement
