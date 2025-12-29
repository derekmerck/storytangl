# SingletonEntity

### *pydantic model* tangl.core.entity.SingletonEntity

Bases: `Singleton`, [`Entity`](entity.md#tangl.core.entity.Entity)

SingletonEntity is a base class for creating unique, immutable entities in StoryTangl.
It ensures that only one instance of each entity exists for a given label.

## Key Features

* **Unique Instance**: Only one instance exists for each unique label. A permanent uid is automatically generated based on the class name and label.
* **Immutability**: Instances are frozen and cannot be modified after creation.
* **Reference-based Serialization**: Can be serialized by reference since they are immutable.

## Usage

## Related Components

* `InheritingSingleton`: Mixin for instance inheritance using from_ref.
* [`SingletonNode`](#tangl.core.graph.SingletonNode): Wrapper for using SingletonEntities in a graph structure.

* **Config:**
  - **frozen**: *bool = True*
* **Fields:**
  - `label ()`
  - `tags ()`
  - `obj_cls ()`
  - `uid (Optional[UUID])`
* **Validators:**
  - `_handle_none_tags` » `tags`
  - `_handle_none_tags` » `with_tags`

#### *property* uid *: UUID*

Return the permanent UID for this object, based on the class name and label

#### *classmethod* clear_instances()

#### *classmethod* discard_instance(label)

#### *classmethod* get_instance(label, create=False)

Retrieves an instance of the singleton entity by its label.

* **Parameters:**
  * **label** (`str`) – The unique label of the entity to retrieve.
  * **create** (`bool`) – Whether the instance should be created if it does not exist.
* **Return type:**
  `Self`
* **Returns:**
  The instance of the singleton entity associated with the label.
* **Raises:**
  **KeyError** – If no instance with the given label exists.

#### has_tags(\*tags)

Condition querying based on tags, enhancing search and categorization.

* **Return type:**
  `bool`

#### *classmethod* load_instances(data)

#### *classmethod* load_instances_from_yaml(resources_module, fn)

#### *field* label *: Optional[str]* *= None* *(name 'label_')*

A short public identifier, usually based on a template name or a truncated uid hash if unspecified, may require uniqueness in some contexts.

#### *field* tags *: Tags* *[Optional]*

Mechanism to classify and filter entities based on assigned characteristics or roles.

#### *field* obj_cls *: Optional[ClassName]* *= None*

The ability to self-cast on instantiation is actually granted by `SelfFactorying`, but the trigger field is included in the base class documentation because in practice, all Entities are self-casting.

## InheritingSingletonEntity

### *pydantic model* tangl.core.entity.InheritingSingletonEntity

Bases: `InheritingSingleton`, [`SingletonEntity`](#tangl.core.entity.SingletonEntity)

* **Config:**
  - **frozen**: *bool = True*
* **Fields:**
  - `uid ()`
  - `label ()`
  - `tags ()`
  - `obj_cls ()`
  - `from_ref ()`
* **Validators:**
  - `_handle_none_tags` » `tags`
  - `_handle_instance_inheritance` » `all fields`

#### *field* from_ref *: Optional[str]* *= None*

The label of the reference entity to inherit attributes from.

## SingletonNode

### *pydantic model* tangl.core.graph.SingletonNode

Bases: [`Entity`](entity.md#tangl.core.entity.Entity)

SingletonNode is a [`Node`](graph_and_node.md#tangl.core.graph.Node) extension that wraps a
[`SingletonEntity`](#tangl.core.entity.SingletonEntity) with instance-specific
state, enabling it to be attached to a graph while maintaining singleton
behavior.

### Key Features

* **Singleton Wrapper**: Wraps a SingletonEntity, providing graph connectivity.  The wrapped SingletonEntity is accessed via the [`reference_entity`](#tangl.core.graph.SingletonNode.reference_entity) property.
* **Instance Variables**: Supports instance-specific variables.  Instance variables must be marked with `json_schema_extra={"instance_var": True}` in the SingletonEntity.
* **Method Rebinding**: Class methods are rebound to the wrapped instance.
* **Dynamic Class Creation**: Provides a method [`create_wrapper_cls()`](#tangl.core.graph.SingletonNode.create_wrapper_cls) to create wrapper classes for specific SingletonEntity types.

### Usage

### Related Components

* [`SingletonEntity`](#tangl.core.entity.SingletonEntity): The base class for singleton entities.
* [`Node`](graph_and_node.md#tangl.core.graph.Node): The base class for graph nodes.

* **Fields:**
  - `uid ()`
  - `label ()`
  - `tags ()`
  - `obj_cls ()`
* **Validators:**
  - `_handle_none_tags` » `tags`
  - `_check_referent_instance` » `all fields`

#### wrapped_cls

alias of [`SingletonEntity`](#tangl.core.entity.SingletonEntity)

#### *property* reference_entity *: [SingletonEntity](#tangl.core.entity.SingletonEntity)*

#### *classmethod* instance_vars(wrapped_cls=None)

#### *classmethod* create_wrapper_cls(name, wrapped_cls)

Class method to dynamically create a new wrapper class given a reference singleton type.

* **Return type:**
  `Type`[`Union`[`TypeVar`(`WrappedSingletonType`, bound= [`SingletonEntity`](#tangl.core.entity.SingletonEntity)), `Self`]]
