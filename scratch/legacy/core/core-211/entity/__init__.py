"""
The Entity and Graph packages provide graph structures, composable nodes, persistence, and traversal capabilities to enable creating interactive fiction narratives. Key concepts are extensive use of inheritance, mixins, and handlers to manage complexity.

Entity is the base class for all managed objects, providing common properties like uid, label, and tags.

There are various "handler" classes that provide functionality to different mixins that can be added to Node classes:

- AvailabilityHandler handles availability logic for Lockable nodes.
- ConditionHandler provides conditional evaluation strategies for Conditional nodes.
- EffectHandler executes side effects defined in HasEffects nodes.
- NamespaceHandler builds namespaces for HasNamespace nodes.
- RenderHandler provides template rendering for Renderable nodes.
- SingletonEntity builds on Entity to ensure only one instance exists per label.
"""

from .entity import Entity, EntityType
from .singleton import SingletonEntity

from .base_handler import BaseEntityHandler
from .base_script_model import BaseScriptItem
from .base_journal_model import BaseJournalItem, StyledJournalItem
