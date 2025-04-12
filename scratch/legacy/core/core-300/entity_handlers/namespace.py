from __future__ import annotations
import logging

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel, StringMap
from tangl.core.handler import BaseHandler, Priority

logger = logging.getLogger(__name__)

class NamespaceHandler(BaseHandler):
    """
    A task handler for managing and aggregating namespaces across entities.
    """
    # @BaseHandler.task_signature
    # def on_get_namespace(entity: HasNamespace, **kwargs) -> StringMap:
    #     ...

    @classmethod
    def strategy(cls, task_id: UniqueLabel = "on_get_namespace",
                 domain: UniqueLabel = "global",
                 priority: int = Priority.NORMAL):
        return super().strategy(task_id, domain, priority)

    @classmethod
    def get_namespace(cls, entity: HasNamespace, **kwargs) -> StringMap:
        """
        Gather and merge namespaces from strategies applied to the given entity.

        :param entity: The entity to be inspected.
        :return: A mapping of local vars.
        """
        try:
            return cls.execute_task(entity, "on_get_namespace", result_mode='merge', **kwargs)
        except Exception as e:
            logger.error(f"Error gathering namespace for entity {entity}: {e}")
            raise

class HasNamespace(BaseModel):
    """
    Entity mixin that provides a cascaded namespace of local variables for computation contexts within an entity. This mechanism provides entities with a scoped set of variables that are relevant to their current state.

    Key Features:
      - `locals`: A dictionary meant to store local variables or values associated with an entity. Initialized with a default factory to ensure each instance has its own distinct dictionary.
      - `_include_locals`: A strategy method for the `NamespaceHandler` to include this entity's locals in the namespace. It is set with the LAST priority, ensuring it overwrites or finalizes the namespace composition, reflecting the most current state of local variables.
    """
    locals: StringMap = Field(default_factory=dict)

    @NamespaceHandler.strategy(priority=Priority.LAST)
    def _include_locals(self, **kwargs) -> StringMap:
        # This runs LAST, so it will overwrite everything else with locals when merged
        return self.locals

    def get_namespace(self, **kwargs) -> StringMap:
        return NamespaceHandler.get_namespace(self, **kwargs)
