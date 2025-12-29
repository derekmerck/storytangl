# Entity

### *pydantic model* tangl.core.entity.Entity

Entities are the fundamental building blocks in StoryTangl. They represent any object
or concept within the story world that needs to be tracked, manipulated, or interacted with.

## Key Features

* **Unique Identification**: Each entity has a uid for system-wide identification.
  The uid is automatically generated if not provided, ensuring uniqueness.
* **Labeling**: Entities can be given human-readable labels for easier reference.
  The label defaults to a shortened version of the uid if not specified.
* **Tagging**: Flexible tagging system for categorization and filtering.
* **Serialization**: Built-in methods for converting to and from dictionary representations.
* **Comparison**: Subclass fields may be excluded from comparison by flagging `json_schema_extras['cmp'] = False` in the pydantic field declaration.

## Usage

```python
from tangl.core.entity import Entity

# Creating a basic entity
entity = Entity(label="example_entity", tags={"important", "active"})

# Accessing properties
print(entity.uid)    # Unique identifier
print(entity.label)  # "example_entity"
print(entity.tags)   # {"important", "active"}

# Checking tags
print(entity.has_tags("important"))  # True
print(entity.has_tags("important", "inactive"))  # False

# Serialization
entity_dict = entity.model_dump()
```

## Mixin Classes

Entities are designed to be extendable through mixins, allowing for flexible behavior composition.

* [`HasNamespace`](mixins_and_handlers.md#tangl.core.entity.handlers.HasNamespace): Adds a namespaces context and local variables.
* [`Lockable`](mixins_and_handlers.md#tangl.core.entity.handlers.Lockable): Adds locking and methods for checking availability.
* [`Conditional`](mixins_and_handlers.md#tangl.core.entity.handlers.Conditional): Adds runtime evaluation.
* [`HasEffects`](mixins_and_handlers.md#tangl.core.entity.handlers.HasEffects): Adds runtime execution.
* `Renderable`: Provides a framework for generating a narrative update.
* [`SelfFactorying`](mixins_and_handlers.md#tangl.core.entity.handlers.SelfFactorying): Enables self-casting to any subclass by using the reserved init var [`obj_cls`](#tangl.core.entity.Entity.obj_cls).

## Related Concepts

* Connected Entities are `Nodes`
* Singleton Entities are `SingletonEntities`

* **Fields:**
  - `uid (uuid.UUID)`
  - `label (str | None)`
  - `tags (set[enum.Enum | str | int])`
  - `obj_cls (str | None)`
* **Validators:**
  - `_handle_none_tags` » `with_tags`
  - `_handle_none_tags` » `tags`

#### *field* uid *: UUID* *[Optional]* *(name 'uid_')*

Unique identifier for each instance for registries and serialization.

#### *field* label *: Optional[str]* *= None* *(name 'label_')*

A short public identifier, usually based on a template name or a truncated uid hash if unspecified, may require uniqueness in some contexts.

#### *field* tags *: Tags* *[Optional]*

Mechanism to classify and filter entities based on assigned characteristics or roles.

#### has_tags(\*tags)

Condition querying based on tags, enhancing search and categorization.

* **Return type:**
  `bool`

#### *classmethod* public_field_names()

Returns a list of constructor parameter names or aliases, if an alias is defined.

* **Return type:**
  `list`[`str`]

#### *field* obj_cls *: Optional[ClassName]* *= None*

The ability to self-cast on instantiation is actually granted by `SelfFactorying`, but the trigger field is included in the base class documentation because in practice, all Entities are self-casting.
