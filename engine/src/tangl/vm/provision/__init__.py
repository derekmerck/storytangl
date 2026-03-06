from .requirement import Requirement, HasRequirement, Dependency, Affordance
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
