Handlers
========

Handlers in StoryTangl are core components that manage various aspects of entity behavior and interaction. They use a strategy pattern to allow for flexible, extensible behavior definition.

Key Concepts
------------

- **Handler**: A class that manages a specific aspect of entity behavior.
- **Strategy**: A method that can be registered with a handler to define or extend behavior.
- **Hook**: A predefined point in the entity lifecycle where strategies can be executed.

Usage
-----

Handlers are typically used by registering strategies with them:

~~~python
from tangl.core.entity.handlers import AvailabilityHandler

class MyEntity(Entity):
    @AvailabilityHandler.strategy()
    def check_availability(self, **kwargs):
        return self.some_condition
~~~

These strategies are then automatically called by the handlers at appropriate times during the entity's lifecycle.

Common Hooks
------------

Scoped handler methods can be hooked by registering a function by task id with a custom handler.

- :code:`on_available`: Determines if an entity is currently available.
- :code:`on_get_namespace`: Retrieves the namespace for an entity.
- :code:`on_get_conditions`: Retrieves the conditions for an entity.
- :code:`on_get_effects`: Retrieves the effects for an entity.
- :code:`on_render`: Renders an entity for output.
- :code:`on_enter`: Executed when entering a node during traversal.
- :code:`on_exit`: Executed when exiting a node during traversal.
- :code:`on_can_associate`: Checks if an association can be formed.
- :code:`on_can_disassociate`: Checks if an association can be removed.
- :code:`on_associate`: Executed when an association between nodes is formed.
- :code:`on_disassociate`: Executed when an association between nodes is removed.
- :code:`on_new`: Executed when creating a new entity.


BaseHandler
-----------

.. autoclass:: tangl.core.handler.BaseHandler
   :members:


Entity Mixins and Handlers
==========================

General features.

Namespace
---------
.. autoclass:: tangl.core.entity.handlers.NamespaceHandler
   :members:

.. autopydantic_model:: tangl.core.entity.handlers.HasNamespace
   :members:

Availability
------------
.. autoclass:: tangl.core.entity.handlers.AvailabilityHandler
   :members:

.. autopydantic_model:: tangl.core.entity.handlers.Lockable
   :members:

Conditions
----------
.. autoclass:: tangl.core.entity.handlers.ConditionHandler
   :members:

.. autopydantic_model:: tangl.core.entity.handlers.Conditional
   :members:


Effects
-------
.. autoclass:: tangl.core.entity.handlers.EffectHandler
   :members:

.. autopydantic_model:: tangl.core.entity.handlers.HasEffects
   :members:


Self-Factorying
---------------
.. autoclass:: tangl.core.entity.handlers.SelfFactoryingHandler
   :members:

.. autoclass:: tangl.core.entity.handlers.SelfFactorying
   :members:


Templated
---------



Node Mixins and Handlers
========================

Features related to connectivity.

Associating
-----------

.. autoclass:: tangl.core.graph.handlers.AssociationHandler
   :members:

.. autopydantic_model:: tangl.core.graph.handlers.Associating
   :members:

Traversal
---------

.. autoclass:: tangl.core.graph.handlers.TraversalHandler
   :members:

.. autopydantic_model:: tangl.core.graph.handlers.TraversableGraph
   :members:

.. autopydantic_model:: tangl.core.graph.handlers.TraversableNode
   :members:


