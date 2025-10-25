from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar, Union, get_type_hints
from uuid import UUID

import pydantic
from pydantic import Field, PrivateAttr

T = TypeVar('T')


def component(func: Optional[Callable] = None, *, field_name: Optional[str] = None):
    """
    Decorator that creates a property which automatically handles storing only component IDs
    while presenting the complete object when accessed.

    The decorated method should return the component when no ID is set.

    Args:
        func: The getter method that provides lookup logic when component not found
        field_name: Optional override for the attribute name used to store the ID
                   (defaults to "_" + method_name + "_id")

    Returns:
        A property descriptor that handles component-ID referencing transparently
    """

    def decorator(func):
        # Determine the property name and ID field name
        prop_name = func.__name__
        id_field_name = field_name or f"_{prop_name}_id"

        # Extract the return type of the function if available
        # This can be used for type checking or class lookup
        return_type = None
        try:
            type_hints = get_type_hints(func)
            if 'return' in type_hints:
                return_type = type_hints['return']
        except (TypeError, ValueError):
            pass

        # Define the getter
        @wraps(func)
        def getter(self):
            # Get the ID value
            component_id = getattr(self, id_field_name, None)

            # If we have an ID, try to get the component from the graph
            if component_id is not None:
                try:
                    if hasattr(self, 'graph') and self.graph is not None:
                        return self.graph.get_node(component_id)
                except (KeyError, AttributeError):
                    # If lookup fails, fall back to the wrapped function
                    pass

            # Fall back to the wrapped function's logic for finding/creating component
            return func(self)

        # Define the setter - stores only the ID
        def setter(self, value):
            if value is None:
                setattr(self, id_field_name, None)
            elif isinstance(value, (str, UUID)):
                setattr(self, id_field_name, value)
            elif hasattr(value, 'uid'):
                setattr(self, id_field_name, value.uid)
            else:
                raise TypeError(f"Cannot set {prop_name} to {type(value)}")

        # Define a deleter that removes the ID reference
        def deleter(self):
            setattr(self, id_field_name, None)

        # Create and return the property
        return property(getter, setter, deleter)

    # Handle both @component and @component(field_name="...")
    if func is None:
        return decorator
    return decorator(func)


# Ensure the model has the necessary ID fields defined
def add_component_fields(cls):
    """
    Class decorator that examines a class for @component decorators and adds
    the corresponding ID fields to the model automatically.

    This should be applied to your Node class.
    """
    # Find all properties created with @component
    component_props = []
    for name, value in cls.__dict__.items():
        if isinstance(value, property) and hasattr(value.fget, '__wrapped__'):
            # This is likely a property created by our @component decorator
            component_props.append(name)

    # Add the ID fields to the model if they don't exist already
    existing_fields = getattr(cls, 'model_fields', {})
    new_fields = {}

    for prop_name in component_props:
        id_field_name = f"_{prop_name}_id"
        if id_field_name not in existing_fields:
            # Add the ID field with appropriate type
            new_fields[id_field_name] = (Optional[UUID], PrivateAttr(default=None))

    # Update the model (approach depends on your pydantic version)
    if hasattr(pydantic, 'create_model'):
        # Pydantic v2 approach
        if new_fields:
            updated_cls = pydantic.create_model(
                cls.__name__,
                __base__=cls,
                **new_fields
            )
            return updated_cls

    # Otherwise, return the original class
    return cls

# Example usage:

import uuid

@add_component_fields
class Node(pydantic.BaseModel):
    uid: UUID = Field(default_factory=uuid.uuid4)
    graph: dict = Field(default_factory=dict)

    @component
    def child(self):
        # Create a new child if none exists
        return Node(uid=uuid.uuid4(), graph=self.graph)


node = Node()
child = node.child
assert node.child is child
assert node._child_id == child.uid


