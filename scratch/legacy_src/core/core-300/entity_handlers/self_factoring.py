from __future__ import annotations
from typing import Type
import logging

from pydantic.root_model import _RootModelMetaclass
from pydantic._internal._model_construction import ModelMetaclass

from tangl.type_hints import Typelike
from tangl.core.handler.base_handler import BaseHandler, Priority
from tangl.utils.inheritance_aware import InheritanceAware
from tangl.utils.property_hints import get_property_return_hints

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class SelfFactoringHandler(BaseHandler):

    # @BaseHandler.task_signature
    # @staticmethod
    # def on_new(cls: Type, **kwargs) -> tuple[Typelike, dict]:
    #     ...

    @staticmethod
    def resolve_base_cls(obj_cls: Typelike):
        """
        Resolve a class descendent of InheritanceAware.
        """
        if obj_cls is None:
            return
        if isinstance(obj_cls, type):
            return obj_cls
        if isinstance(obj_cls, str):
            new_cls = InheritanceAware.get_subclass_by_name(obj_cls)
            if new_cls is None:
                raise ValueError(f"Unknown subclass name: {obj_cls}")
            return new_cls
        raise ValueError(f"Invalid obj_cls for init: {obj_cls}")

    @BaseHandler.strategy('on_new', priority=Priority.FIRST)
    @staticmethod
    def _resolve_base_cls(base_cls: Type, obj_cls: Typelike = None,
                          **kwargs) -> tuple[Typelike, dict]:
        """
        Dynamically reassign class type by parameter.  This is used by the deserializer
        to dynamically allow Entity(obj_cls="MyEntity", *args, **kwargs) to be new'd as
        if MyEntity(*args, **kwargs) had been called directly.

        This is a very early call in the priority queue and consumes the 'obj_cls' kwarg,
        if it exists, so any later calls can still override 'base_cls'.
        """
        new_cls = SelfFactoringHandler.resolve_base_cls(obj_cls) or base_cls
        if new_cls is base_cls:
            return
        return new_cls, kwargs

    @classmethod
    def resolve_children_kwargs(cls, base_cls, data) -> dict:
        """
        Parses unknown fields with property hints into children data annotated
        with the default nominal object type.
        """
        if not hasattr(base_cls, "model_fields"):
            return data
        ignore_fields = {"parent", "root", "children"}
        model_fields = { x.strip("_") for x in base_cls.public_field_names() }
        # model_fields = { x.strip("_") for x in base_cls.model_fields.keys() }
        unknown_fields = set(data.keys()) - model_fields - ignore_fields
        logger.debug(f"Found unknown fields {unknown_fields}")
        children_data = []
        if unknown_fields:
            property_return_types = get_property_return_hints(base_cls)
            logger.debug(f"Found property return hints for {base_cls}: {property_return_types}")
            for key in unknown_fields:
                if hint := property_return_types.get(key):
                    ret_mode, child_cls = hint
                    logger.debug(f"Discovered property return hint for {key}: {hint}")
                    property_kwarg = data.pop(key)
                    logger.debug(f"property kwarg is {property_kwarg}")
                    if ret_mode == "discrete":
                        property_kwarg.setdefault("obj_cls", child_cls)
                        children_data.append(property_kwarg)
                        logger.debug(f"Added discrete child as {key}: {child_cls}")
                    elif ret_mode == "collection":
                        # could be a dict or list
                        if isinstance(property_kwarg, list):
                            for i, v in enumerate(property_kwarg):
                                v.setdefault("obj_cls", child_cls)
                                v.setdefault("label", f"{key[0:3]}-{i}")
                            children_data.extend(property_kwarg)
                            logger.debug(f"Added list of children as {key}: list[{child_cls}]")
                        elif isinstance(property_kwarg, dict) and all(isinstance(v, dict) for v in property_kwarg.values()):
                            for k, v in property_kwarg.items():
                                v.setdefault("obj_cls", child_cls)
                                v.setdefault("label", k)
                            logger.debug(f"Added dict of children as {key}: dict[{child_cls}]")
                            children_data.extend(property_kwarg.values())
                        else:
                            raise TypeError(f"Unsupported collection return collection {type(property_kwarg)}")
                    else:
                        raise TypeError(f"Unsupported property return hint {ret_mode}")
                else:
                    raise TypeError(f"No return hint for unknown field {key} in {base_cls}")

        if children_data:
            logger.debug( "adding children_data field" )
            data["children_data"] = children_data

        return data

    @classmethod
    def create_node(cls, *, obj_cls: Typelike, **kwargs):
        new_cls = cls.resolve_base_cls(obj_cls)
        kwargs = cls.resolve_children_kwargs(new_cls, kwargs)
        logger.debug(f"invoking create node: {new_cls}, {str(kwargs)}")
        children_data = kwargs.pop("children_data", [])
        instance = new_cls.__call__(**kwargs)
        for child_data in children_data:
            child = cls.create_node(**child_data, parent=instance)
        return instance

class SelfFactoring(type):
    """
    Metaclass that can perform pre-processing during instance creation.
    """
    def __call__(base_cls: Type, *args, **kwargs):
        """
        Calls "on_new" strategies for instance creation to resolve obj_cls and kwargs
        """
        logger.debug(f"in call: {str(kwargs)}")
        new_cls, kwargs = SelfFactoringHandler.execute_task(base_cls, 'on_new',
                                                             result_mode="pipeline", **kwargs)

        if new_cls is not base_cls:
            # Re-invoke
            instance = new_cls.__new__(new_cls, *args, **kwargs)
            if isinstance(instance, new_cls):
                # only call __init__ if __new__ returned the _new_class_ instance type
                instance.__init__(*args, **kwargs)
        else:
            instance = super().__call__(*args, **kwargs)
            # an instance of the passed type will be automatically initialized

        return instance

    def __new__(mcs, name, bases, attrs):
        # Inject InheritanceAware if it's not already in the bases
        logger.debug(f"in new: {name} {bases} {attrs}")
        # Check if InheritanceAware is already in the class hierarchy
        if not any(issubclass(b, InheritanceAware) for b in bases):
            bases = (InheritanceAware,) + bases

        # Create the class
        cls = super().__new__(mcs, name, bases, attrs)
        return cls


# Pydantic base-model compatible
SelfFactoringModel = type("SelfFactoringModel", (SelfFactoring, ModelMetaclass), {})
