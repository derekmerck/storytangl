"""
.. currentmodule:: tangl.vm.provision

Constraint, offer, and resolver mechanisms for runtime provisioning.

Conceptual layers
-----------------

1. Constraint graph edges

   - :class:`Requirement` describes an unsatisfied resource contract.
   - :class:`HasRequirement` embeds one requirement into a registry-aware
     carrier.
   - :class:`Dependency`, :class:`Affordance`, and :class:`Fanout` carry
     requirements through the graph topology.
     graph topology.

2. Offer protocol

   - :class:`ProvisionPolicy` filters allowed offer kinds.
   - :class:`ProvisionOffer` records one ranked, deferred candidate.
   - :class:`Provisioner` defines the structural protocol used by concrete
     offer sources.

3. Provisioner implementations

   - :class:`FindProvisioner` surfaces existing in-graph providers.
   - :class:`TemplateProvisioner`, :class:`TokenProvisioner`, and
     :class:`InlineTemplateProvisioner` synthesize create-style offers.
   - :class:`StubProvisioner` keeps preview flows alive when stub linkage is
     allowed.
   - :class:`UpdateCloneProvisioner` synthesizes deferred UPDATE and CLONE
     offers from compatible FIND and CREATE candidates.

4. Orchestrated resolution

   - :class:`Resolver` gathers, ranks, filters, previews, and binds offers back
     into frontier dependencies.

Design intent
-------------
This package owns mechanism rather than narrative policy. Story-specific meaning
for requirements and providers lives in :mod:`tangl.story`.
"""

from .requirement import Requirement, HasRequirement, Dependency, Affordance, Fanout
from .preview import Blocker, ViabilityResult
from .scope import (
    admitted,
    build_plan,
    context_prefix,
    is_qualified_path,
    leaf_identifier,
    levenshtein_components,
    resolve_target_path,
    scope_distance,
    scope_prefix,
    target_context_candidates,
)
from .provisioner import (
    ProvisionPolicy,
    ProvisionOffer,
    Provisioner,
    TemplateProvisioner,
    TokenProvisioner,
    InlineTemplateProvisioner,
    FindProvisioner,
    StubProvisioner,
    UpdateCloneProvisioner,
    CloneProvisioner,
)
from .resolver import Resolver


# Legacy compatibility alias retained during namespace cutover.
ProvisioningPolicy = ProvisionPolicy

__all__ = [
    "Requirement",
    "HasRequirement",
    "Dependency",
    "Affordance",
    "Fanout",
    "Blocker",
    "ViabilityResult",
    "admitted",
    "build_plan",
    "context_prefix",
    "is_qualified_path",
    "leaf_identifier",
    "levenshtein_components",
    "resolve_target_path",
    "scope_distance",
    "scope_prefix",
    "target_context_candidates",
    "ProvisionPolicy",
    "ProvisioningPolicy",
    "ProvisionOffer",
    "Provisioner",
    "TemplateProvisioner",
    "TokenProvisioner",
    "InlineTemplateProvisioner",
    "FindProvisioner",
    "StubProvisioner",
    "UpdateCloneProvisioner",
    "CloneProvisioner",
    "Resolver",
]
