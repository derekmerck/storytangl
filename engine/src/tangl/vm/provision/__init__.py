# tangl/vm/__init__.py
"""
Frontier planning primitives.

This subpackage defines the minimal abstractions used to extend the *resolution
frontier* during :data:`~tangl.vm.frame.ResolutionPhase.PLANNING`:

- :class:`~tangl.vm.planning.requirement.Requirement` expresses a need
  (dependency or affordance) with a provisioning policy.
- :class:`~tangl.vm.planning.provisioning.Provisioner` is the default provider
  that searches registries, updates or clones, or creates new nodes from templates.
- :class:`~tangl.vm.planning.offer.ProvisionOffer` wraps a provisioner call as a proposal.
- :mod:`~tangl.vm.planning.simple_planning_handlers` wires the phase bus:
  collect offers → select & apply → compose a planning receipt.

All types are intentionally small and generic so domains can publish richer
builders without modifying core VM code.
"""
from .requirement import ProvisioningPolicy, Requirement
from .provisioner import Provisioner
from .open_edge import Dependency, Affordance
from .offer import BuildReceipt, ProvisionOffer, PlanningReceipt
from .offers import ProvisionCost, DependencyOffer, AffordanceOffer
