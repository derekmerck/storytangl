from __future__ import annotations

import logging
from logging import getLogger
import random
from typing import Any

from pydantic import BaseModel, Field

from tangl.type_hints import Strings
from tangl.utils.safe_builtins import safe_builtins
from .. import EntityType
from ..base_handler import BaseEntityHandler
from .namespace import NamespaceHandler, HasNamespace

logger = getLogger("tangl.effects")
logger.setLevel(logging.WARNING)

class EffectHandler(BaseEntityHandler):
    """
    A handler class for managing and applying effect strategies to Node classes.
    Provides functionality to execute effects using dynamic namespaces.

    KeyFeatures:
      - `apply_effects(entity)`: Applies effects attached to entity
    """

    default_strategy_annotation = "is_effect_strategy"

    @classmethod
    def apply_effect(cls, expr: str, ns: dict = None) -> bool:
        """
        Execute an effect expression within the given namespace.

        :param expr: The effect expression to be executed.
        :param ns: A dict of variables to be used in the expression.
        :return bool: True if successful
        """
        try:
            ns = ns or {}
            exec( expr, {'random': random, '__builtins__': safe_builtins}, ns )
            return True
        except (SyntaxError, TypeError, KeyError, AttributeError, NameError):
            logger.critical(f"Failed to apply '{expr}'")
            raise

    @classmethod
    def apply_effects_to(cls, effects: Strings, entity: EntityType) -> bool:
        if not effects:
            return True
        ns = entity.get_namespace()
        ns = {**ns}
        for effect in effects:
            cls.apply_effect(effect, ns)

        # Updates to entity.locals need to be handled explicitly
        entity_locals = list( entity.locals.keys() )
        for k in entity_locals:
            if k in ns and entity.locals[k] != ns[k]:
                entity.locals[k] = ns[k]

        return True

    @classmethod
    def apply_effects(cls, entity: HasEffects) -> bool:
        effects = cls.invoke_strategies(entity, result_handler="flatten")  # type: Strings
        return cls.apply_effects_to(effects, entity)


class HasEffects(HasNamespace):
    """
    A mixin class that adds the capability of effects to Node classes.
    It provides strategies to execute effects.

    :ivar effects: List of effects to be applied based on node interactions.

    :Methods:
    - :meth:`apply_effects`: Executes all effects associated with the node.

    """
    effects: Strings = Field(default_factory=list)

    @EffectHandler.strategy
    def _get_effects(self):
        return self.effects

    def apply_effects(self):
        """
        Apply all effects defined for the entity.
        """
        logger.debug("Calling effect Handler")
        return EffectHandler.apply_effects(self)

    def apply_effects_to(self, entity: EntityType):
        """
        Apply all effects defined for the entity to target node.
        """
        logger.debug("Calling effect Handler")
        return EffectHandler.apply_effects_to(self.effects, entity)
