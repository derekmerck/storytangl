# Handlers

Handlers in StoryTangl are core components that manage various aspects of entity behavior and interaction. They use a strategy pattern to allow for flexible, extensible behavior definition.

## Key Concepts

- **Handler**: A class that manages a specific aspect of entity behavior.
- **Strategy**: A method that can be registered with a handler to define or extend behavior.
- **Hook**: A predefined point in the entity lifecycle where strategies can be executed.

## Usage

Handlers are typically used by registering strategies with them:

~~~python
from tangl.core.entity.handlers import AvailabilityHandler

class MyEntity(Entity):
: @AvailabilityHandler.strategy()
  def check_availability(self, 
  <br/>
  ```
  **
  ```
  <br/>
  kwargs):
  <br/>
  > return self.some_condition

~~~

These strategies are then automatically called by the handlers at appropriate times during the entity’s lifecycle.

## Common Hooks

Scoped handler methods can be hooked by registering a function by task id with a custom handler.

- `on_available`: Determines if an entity is currently available.
- `on_get_namespace`: Retrieves the namespace for an entity.
- `on_get_conditions`: Retrieves the conditions for an entity.
- `on_get_effects`: Retrieves the effects for an entity.
- `on_render`: Renders an entity for output.
- `on_enter`: Executed when entering a node during traversal.
- `on_exit`: Executed when exiting a node during traversal.
- `on_can_associate`: Checks if an association can be formed.
- `on_can_disassociate`: Checks if an association can be removed.
- `on_associate`: Executed when an association between nodes is formed.
- `on_disassociate`: Executed when an association between nodes is removed.
- `on_new`: Executed when creating a new entity.

## BaseHandler

### *class* tangl.core.handler.BaseHandler

BaseHandler provides a “contextual dispatch” system.  It resolves and
executes an ordered list of functions for a task and calling class based on:

- Behavioral grouping (“task” handlers)
- Class hierarchy (MRO)
- External categorization (“domain” plugins)

It can also finalize the result in several different ways, from returning
the entire list of results, an iterator of method calls, to flattening to a
single primitive type.

Functions can be registered directly or using a decorator.

#### *classmethod* register_task_signature(task_id, strategy)

Registering a task signature provides some measure of Runtime type checking.

# Entity Mixins and Handlers

General features.

## Namespace

### *class* tangl.core.entity.handlers.NamespaceHandler

A task handler for managing and aggregating namespaces across entities.

#### *classmethod* get_namespace(entity, \*\*kwargs)

Gather and merge namespaces from strategies applied to the given entity.

* **Parameters:**
  **entity** ([`HasNamespace`](#tangl.core.entity.handlers.HasNamespace)) – The entity to be inspected.
* **Return type:**
  `dict`[`str`, `Any`]
* **Returns:**
  A mapping of local vars.

### *pydantic model* tangl.core.entity.handlers.HasNamespace

Entity mixin that provides a cascaded namespace of local variables for computation contexts within an entity. This mechanism provides entities with a scoped set of variables that are relevant to their current state.

Key Features:
: - locals: A dictionary meant to store local variables or values associated with an entity. Initialized with a default factory to ensure each instance has its own distinct dictionary.
  - \_include_locals: A strategy method for the NamespaceHandler to include this entity’s locals in the namespace. It is set with the LAST priority, ensuring it overwrites or finalizes the namespace composition, reflecting the most current state of local variables.

* **Fields:**
  - `locals (dict[str, Any])`

#### *field* locals *: StringMap* *[Optional]*

#### get_namespace(\*\*kwargs)

* **Return type:**
  `dict`[`str`, `Any`]

## Availability

### *class* tangl.core.entity.handlers.AvailabilityHandler

AvailabilityHandler manages the availability status of entities in StoryTangl.
It determines whether an entity can be interacted with based on various conditions.

### Key Features

* **Availability Checking**: Determines if an entity is currently available.
* **Force Availability**: Allows forcing an entity to be available, overriding other conditions.
* **Strategy-based**: Uses the strategy pattern for flexible availability logic.

### Main Hooks

* `on_available`: Called to determine if an entity is currently available.

### Usage

```python
from tangl.core.entity.handlers import AvailabilityHandler, Lockable

class MyEntity(Lockable, Entity):
    @AvailabilityHandler.strategy()
    def check_custom_availability(self, **kwargs):
        return self.some_custom_condition

entity = MyEntity()
is_available = AvailabilityHandler.available(entity)
```

### Considerations

* Multiple availability strategies can be registered for a single entity.
* All registered strategies must return True for an entity to be considered available.
* The order of strategy execution can be controlled using the priority parameter.

### Common Strategies

1. **Basic Availability**: Check if an entity is not locked.
2. **Condition-based Availability**: Check if certain conditions are met.
3. **Time-based Availability**: Check if the entity is available based on in-game time.

### Related Components

* [`Lockable`](#tangl.core.entity.handlers.Lockable): Mixin for basic locking functionality.
* [`Conditional`](#tangl.core.entity.handlers.Conditional): Mixin for condition-based availability.

#### *classmethod* available(entity, force=False, \*\*kwargs)

#### Parameters
- entity: The entity being checked for availability.
- \*\*kwargs: Additional keyword arguments that might affect availability.

#### Returns
- bool: True if the entity is available, False otherwise.

Check if entity is available for use.

* **Parameters:**
  **entity** ([`Lockable`](#tangl.core.entity.handlers.Lockable)) – The entity to be examined.
* **Return type:**
  `bool`
* **Returns:**
  A boolean.

### *pydantic model* tangl.core.entity.handlers.Lockable

Allows an entity to be manually locked from availability within the game.

- Key Features:
  - locked: A boolean attribute indicating if the entity is locked.
  - forced: A boolean attribute indicating that the entity or its parents has been ‘forced’ to be available, overriding any other conditions.
  - available(): Utilizes AvailabilityHandler to determine if the entity is available based on the locked status and other custom strategies.

* **Fields:**
  - `locked (bool)`
  - `forced_ (bool)`

#### *field* locked *: bool* *= False*

#### *field* forced_ *: bool* *= False*

#### lock()

Lock an entity.

#### unlock(force=False)

Unlock an entity.

* **Parameters:**
  **force** (`bool`) – A boolean indicating that this is a ‘force’ unlock that overrides all other availability conditions.

#### *property* forced

#### available(\*\*kwargs)

* **Return type:**
  `bool`

## Conditions

### *class* tangl.core.entity.handlers.ConditionHandler

A handler class for managing and evaluating conditional strategies in Entity classes.
Provides functionality to check conditions using dynamic namespaces.

KeyFeatures:
: - check_conditions(entity): Evaluates conditions attached to entity
  - check_conditions_satisfied_by(conditions, entity): Evaluates conditions give a reference entity

#### *classmethod* check_expr(expr, ns=None)

Evaluate a expression string within the given namespace.

* **Parameters:**
  * **expr** (`str`) – The expression string to be evaluated.
  * **ns** (`Mapping`) – A mapping of variables to be used in the condition.
* **Returns:**
  The result of the condition evaluation.

### *pydantic model* tangl.core.entity.handlers.Conditional

A mixin class that adds conditional logic to Entity classes.
It provides strategies to check conditions and determine entity availability.

Key Features:
: - conditions: A list of conditions that determine if certain actions or effects can be applied.
  - check_conditions(): Method that interfaces with ConditionHandler to evaluate conditions.
  - check_satisfied_by(entity): Method that interfaces with ConditionHandler to evaluate another entity with respect to this entity’s conditions.

* **Fields:**
  - `conditions (Strings)`

#### *field* conditions *: Strings* *[Optional]*

#### check_conditions(\*\*kwargs)

Check if all conditions for the entity are met.

* **Return type:**
  `bool`
* **Returns:**
  True if conditions are met, False otherwise.

#### check_satisfied_by(entity)

Check if all conditions for this Entity are met by a different Entity.

* **Return type:**
  `bool`
* **Returns:**
  True if conditions are met, False otherwise.

## Effects

### *class* tangl.core.entity.handlers.EffectHandler

A handler class for managing and applying effect strategies for Entities.
Provides functionality to execute effects using dynamic namespaces.

KeyFeatures:
: - apply_effects(entity): Applies effects attached to entity

#### *classmethod* apply_effect(expr, ns=None)

Execute an effect expression within the given namespace.

* **Parameters:**
  * **expr** (`str`) – The effect expression to be executed.
  * **ns** (`Mapping`) – A dict of variables to be used in the expression.
* **Return bool:**
  True if successful
* **Return type:**
  `bool`

### *pydantic model* tangl.core.entity.handlers.HasEffects

A mixin class that adds the capability of effects to Node classes.
It provides strategies to execute effects.

* **Variables:**
  **effects** – List of effects to be applied based on node interactions.
* **Methods:**

- [`apply_effects()`](#tangl.core.entity.handlers.HasEffects.apply_effects): Executes all effects associated with the node.

* **Fields:**
  - `effects (Strings)`

#### *field* effects *: Strings* *[Optional]*

#### apply_effects()

Apply all effects defined for the entity.

#### apply_effects_to(entity)

Apply all effects defined for the entity to target node.

## Self-Factorying

### *class* tangl.core.entity.handlers.SelfFactoryingHandler

#### *static* resolve_base_cls(obj_cls)

Resolve a class descendent of InheritanceAware.

#### *classmethod* resolve_children_kwargs(base_cls, data)

Parses unknown fields with property hints into children data annotated
with the default nominal object type.

* **Return type:**
  `dict`

### *class* tangl.core.entity.handlers.SelfFactorying(name, bases, attrs)

Metaclass that can perform pre-processing during instance creation.

## Templated

# Node Mixins and Handlers

Features related to connectivity.

## Associating

### *class* tangl.core.graph.handlers.AssociationHandler

#### *classmethod* associate_with(node, other, as_parent=False, \*\*kwargs)

If ‘as_parent’, then add other as a child of node, otherwise, add them
as children of one-another without reparenting either.

#### *classmethod* disassociate_from(node, other, \*\*kwargs)

Calls remove child on both, if one is the parent of the other, they will be unparented.

### *pydantic model* tangl.core.graph.handlers.Associating

* **Fields:**

#### *property* associates *: list[[Associating](#tangl.core.graph.handlers.Associating)]*

#### can_associate_with(other, as_parent=False, \*\*kwargs)

* **Return type:**
  `bool`

#### associate_with(other, as_parent=False, \*\*kwargs)

#### can_disassociate_from(other, \*\*kwargs)

* **Return type:**
  `bool`

#### disassociate_from(other, \*\*kwargs)

## Traversal

### *class* tangl.core.graph.handlers.TraversalHandler

#### on_enter(\*\*kwargs)

Called when the graph cursor tries to arrive at a new node.  This
may happen automatically according to activation directives, or be
triggered manually by selecting an edge with no activation rule.

If an Edge node is returned, it is assumed to be a \_redirect_ or
\_continue_ directive, and the traversal handler will attempt to
follow it.

Redirects activate FIRST, \_before_ any node update logic.  Continues
activate LAST, \_after_ the node update is complete.

If no continue is provided, the graph cursor “settles” on the last
entered node and waits for a manual selection.

* **Return type:**
  `Optional`[`EdgeProtocol`]

#### on_exit(\*\*kwargs)

Called on the predecessor for clean-up when the graph cursor follows an edge.

#### *classmethod* enter_node(node, ignore_redirects=False, \*\*kwargs)

Recursively follows edges and returns the final node.

If jumping directly to an unrelated node, the prior node’s exit status cannot be
updated here, as there is no notion of \_where_ the cursor came from.  Use a temporary
edge object and following it.

* **Return type:**
  [`TraversableNode`](#tangl.core.graph.handlers.TraversableNode)

#### *classmethod* exit_node(node, \*\*kwargs)

Clean up and do post-visit bookkeeping

### *pydantic model* tangl.core.graph.handlers.TraversableGraph

* **Fields:**
  - `cursor_id (uuid.UUID)`

#### *field* cursor_id *: UUID* *= None*

#### *property* cursor *: [TraversableNode](#tangl.core.graph.handlers.TraversableNode)*

#### follow_edge(edge, \*\*kwargs)

#### goto_node(new_cursor, \*\*kwargs)

#### find_entry_node()

* **Return type:**
  [`TraversableNode`](#tangl.core.graph.handlers.TraversableNode)

#### enter(\*\*kwargs)

#### exit(\*\*kwargs)

### *pydantic model* tangl.core.graph.handlers.TraversableNode

All nodes may have parent and child relationships, but not all nodes are
“Traversable” within the “story-as-graph” metaphor.

Only nodes that help direct the narrative from the beginning of a scene to
the end of a scene are considered “Traversable”. These nodes are generally
individual narrative passages (“Blocks”), collections of related passages
(“Scenes”), or connections between passages (“Actions”).

Action edges may be explicit – a choice the player must actively  make, or
implicit, as in an automatic redirection prior to or after a narrative event.

Moving the graph cursor to a new node uses two task callbacks: “on_enter”,
and “on_exit”.  Both can be broken down to priority-ordered stages.

Exit:
- Bookkeeping (Priority.EARLY) – note updates and process outputs
- Clean up (Priority.NORMAL)

Enter:
- Redirection (Priority.FIRST) – check if the node wants to refer the cursor

> to somewhere else prior to handling the node (jump or jnr without exit)
- Validation (Priority.EARLY) – double-check that the node admits entry given
  the current graph state
- Update (Priority.NORMAL) – execute state updates
- Processing (Priority.LATE) – handle any dynamic behaviors assigned to the node
- Continues (Priority.LAST) – check if the node wants to refer the cursor to
  somewhere else after handling the node (jump or jnr with exit)

* **Fields:**
  - `visited (bool)`
  - `wants_exit (bool)`
  - `graph (tangl.core.graph.handlers.traversal.TraversableGraph)`

#### *field* visited *: bool* *= False*

#### *field* wants_exit *: bool* *= False*

#### *field* graph *: TraversableGraph* *[Optional]*

#### *property* edges *: List[[Edge](graph_and_node.md#tangl.core.graph.Edge)]*

#### *property* redirects *: list[[Edge](graph_and_node.md#tangl.core.graph.Edge)]*

#### *property* continues *: list[[Edge](graph_and_node.md#tangl.core.graph.Edge)]*

#### enter(\*\*kwargs)

#### exit(\*\*kwargs)

#### find_entry_node()

* **Return type:**
  [`TraversableNode`](#tangl.core.graph.handlers.TraversableNode)

#### *property* is_entry *: bool*
