from __future__ import annotations
import logging

from pydantic import BaseModel

from tangl.type_hints import UniqueLabel
from tangl.core.handler import BaseHandler, Priority

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class AvailabilityHandler(BaseHandler):
    """
    AvailabilityHandler manages the availability status of entities in StoryTangl.
    It determines whether an entity can be interacted with based on various conditions.

    Key Features
    ------------
    * **Availability Checking**: Determines if an entity is currently available.
    * **Force Availability**: Allows forcing an entity to be available, overriding other conditions.
    * **Strategy-based**: Uses the strategy pattern for flexible availability logic.

    Main Hooks
    ----------
    * :code:`on_available`: Called to determine if an entity is currently available.

    Usage
    -----
    .. code-block:: python

        from tangl.core.entity.handlers import AvailabilityHandler, Lockable

        class MyEntity(Lockable, Entity):
            @AvailabilityHandler.strategy()
            def check_custom_availability(self, **kwargs):
                return self.some_custom_condition

        entity = MyEntity()
        is_available = AvailabilityHandler.available(entity)

    Considerations
    --------------
    * Multiple availability strategies can be registered for a single entity.
    * All registered strategies must return True for an entity to be considered available.
    * The order of strategy execution can be controlled using the `priority` parameter.

    Common Strategies
    -----------------
    1. **Basic Availability**: Check if an entity is not locked.
    2. **Condition-based Availability**: Check if certain conditions are met.
    3. **Time-based Availability**: Check if the entity is available based on in-game time.

    Related Components
    ------------------
    * :class:`~tangl.core.entity.handlers.Lockable`: Mixin for basic locking functionality.
    * :class:`~tangl.core.entity.handlers.Conditional`: Mixin for condition-based availability.
    """
    # @BaseHandler.task_signature
    # def on_available(entity: Lockable, **kwargs) -> bool:
    #     ...

    @classmethod
    def strategy(cls, task_id: UniqueLabel = "on_available",
                 domain: UniqueLabel = "global",
                 priority: int = Priority.NORMAL):
        return super().strategy(task_id, domain, priority)

    @classmethod
    def available(cls, entity: Lockable, force: bool = False, **kwargs) -> bool:
        """

        #### Parameters
        - `entity`: The entity being checked for availability.
        - `**kwargs`: Additional keyword arguments that might affect availability.

        #### Returns
        - `bool`: True if the entity is available, False otherwise.

        Check if entity is available for use.

        :param entity: The entity to be examined.
        :return: A boolean.
        """
        if force:
            entity.unlock(force=True)
        if entity.forced:
            return True
        try:
            return cls.execute_task(entity, "on_available", result_mode="all_true", **kwargs)
        except Exception as e:
            logger.error(f"Error determining availability for entity {entity}: {e}")
            return False

class Lockable(BaseModel):
    """
    Allows an entity to be manually locked from availability within the game.

    - Key Features:
      - `locked`: A boolean attribute indicating if the entity is locked.
      - `forced`: A boolean attribute indicating that the entity or its parents has been 'forced' to be available, overriding any other conditions.
      - `available()`: Utilizes `AvailabilityHandler` to determine if the entity is available based on the `locked` status and other custom strategies.
    """
    locked: bool = False
    forced_: bool = False

    @AvailabilityHandler.strategy()
    def _is_unlocked(self, **kwargs) -> bool:
        return not self.locked

    def lock(self):
        """
        Lock an entity.
        """
        self.locked = True

    def unlock(self, force: bool = False):
        """
        Unlock an entity.

        :param force: A boolean indicating that this is a 'force' unlock that overrides all other availability conditions.
        """
        self.locked = False
        if force:
            self.forced_ = True

    @property
    def forced(self):
        if self.forced_:
            return True
        elif hasattr(self, 'parent') and self.parent and self.parent.forced:
            return True
        return False

    def available(self: Lockable, **kwargs) -> bool:
        result = AvailabilityHandler.available(self, **kwargs)
        logger.debug(f"Available for entity {self}: {result}")
        return result
