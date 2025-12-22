"""
```
core/factory/template.py (THIS FILE)
├── Template[ET]              # Generic template for any Entity
├── ScopeSelectable           # Pattern-based scope matching
├── HierarchicalTemplate[GIT] # Tree of templates with auto-paths
└── Factory                   # Registry + materialization

story/templates/
├── StoryScript(HierarchicalTemplate)         # Root of story hierarchy, contains Scenes, Actors, Locations
├── SceneScript(HierarchicalTemplate[Scene])  # Contains blocks, affordances
├── BlockScript(HierarchicalTemplate[Block])  # Contains inline items
└── ActorScript(Template[Actor])              # Leaf template

vm/provision/
└── Uses Factory to find and materialize templates
```

**Key Principle:** `Template` knows NOTHING about stories, blocks, actors, etc.

Base Templates:

1. Hold semi-structured data for Entities
2. Serialization
    • unstructure_as_template() round-trips to “script format”
    • unstructure_for_materialize() produces a payload suitable for Entity.structure() (or obj_cls.structure())

Hierarchical Templates:

1. Organization
    • Hierarchical templates get stable path identifiers (preorder traversal deterministic).
    • Flattening produces a registry of templates keyed by path.
2. Scope testing
    • A nested template is valid under its parent path by default.
    • Optionally also restricted by tags on any ancestor of the selector.
3. Materialization
    • templ.materialize() creates _one_ realized entity, non-recursive
    • No provisioning, no dependency resolution, no scene creation

Templates need not be defined as Generic as long as they indicate an
appropriate fallback type in get_default_obj_cls().  This obviates the
need to import the ET at the top level and reduces the risk of recursive
definitions.  i.e., Template modules are _independent_ of their ET at
the top level import.
"""

from .template import Template
from .hierarchical_template import HierarchicalTemplate, ScopeSelectable
from .factory import Factory
