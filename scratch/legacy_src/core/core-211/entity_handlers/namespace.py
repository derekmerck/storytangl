from pydantic import BaseModel, Field
from logging import getLogger

from ..base_handler import BaseEntityHandler
from ..entity import EntityType

logger = getLogger("tangl.ns")

class NamespaceHandler(BaseEntityHandler):
    """
    A specialized handler for managing and aggregating namespaces across entities.

    Key Features:
      - `get_namespace(entity)`: Gathers and merges namespaces from all contributing entity mixins into a single namespace dictionary.
    """

    default_strategy_annotation = "namespace_strategy"

    @classmethod
    def get_namespace(cls, entity: EntityType) -> dict:
        """
        Gather and merge namespaces from strategies applied to the given entity.

        :param entity: The entity to be examined.
        :return: A mapping of cascaded local vars from superclasses.
        """
        try:
            return cls.invoke_strategies(entity, result_handler='merge')
        except Exception as e:
            logger.error(f"Error gathering namespace for entity {entity}: {e}")
            return {}


class HasNamespace(BaseModel):
    """
    Acts as an entity mixin that provides a cascaded namespace of local values, crucial for computation contexts within an entity. This mechanism allows entities to maintain a scoped set of variables that are relevant to their current state or actions.

    Key Features:
      - `locals`: A dictionary meant to store local variables or values associated with an entity. Initialized with a default factory to ensure each instance has its own distinct dictionary.
      - `_include_locals`: A strategy method for the `NamespaceHandler` to include this entity's locals in the namespace. It's set with the highest priority (`100`), ensuring it overwrites or finalizes the namespace composition, reflecting the most current state of local variables.
    """

    # Entity mixin providing a cascaded namespace of local values for computation

    locals: dict = Field(default_factory=dict)

    @NamespaceHandler.strategy
    def _include_locals(self):
        return self.locals
    # setting this to run last, so it will overwrite everything else
    _include_locals.strategy_priority = 100

    def get_namespace(self: EntityType) -> dict:
        return NamespaceHandler.get_namespace(self)

