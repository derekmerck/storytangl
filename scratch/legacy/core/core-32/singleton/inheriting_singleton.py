from typing import Optional

from pydantic import model_validator, BaseModel, Field

from tangl.type_hints import UniqueLabel
from .singleton import Singleton


class InheritingSingleton(Singleton):
    """
    A Singleton mixin that supports attribute inheritance from existing instances.

    Attributes are inherited from a reference instance and can be selectively overridden.
    This creates an inheritance chain without requiring class inheritance.  The inheritance
    is controlled by the 'from_ref' keyword argument.

    Be careful to load them in order, the code does not provide any dependency resolution.

    Example:
        base = MySingleton(label="base", value=1, other=2)
        child = MySingleton(label="child", from_ref="base", value=3)
        # child.value == 3, child.other == 2

    Parameters:
        from_ref (UniqueLabel): The label of the reference entity to inherit attributes from.
    """
    from_ref: Optional[UniqueLabel] = Field(None, init_var=True)
    """The label of the reference entity to inherit attributes from.
    Consumed by initialization."""

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @classmethod
    def _set_defaults_from_refs(cls, data):
        if from_ref := data.get('from_ref'):
            ref_instance = cls._instances[from_ref]

            if not ref_instance:
                raise KeyError(
                    f"Cannot inherit from non-existent instance: {from_ref} "
                    f"while creating {data.get('label', '<unknown>')}"
                )
            defaults = BaseModel.model_dump(ref_instance,
                exclude_unset=True, exclude_defaults=True, exclude_none=True,
                exclude={"uid", "label", "from_ref"})
            for k, v in defaults.items():
                if k in data:
                    # include items from reference class in collections
                    if isinstance(data[k], set):
                        data[k] = data[k].union(v)
                    elif isinstance(data[k], dict):
                        data[k] = v | data[k]
                    elif isinstance(data[k], (list, tuple)):
                        data[k].extend(v)
                else:
                    data.setdefault(k, v)
        return data

    # # Track inheritance chain for debugging/visualization
    # inheritance_chain_: list[str] = Field(default_factory=list)
    #
    # @model_validator(mode='before')
    # @classmethod
    # def _handle_instance_inheritance(cls: type[Singleton, Self], data: dict) -> dict:
    #     # Handle both from_ref and from alias
    #     from_ref = data.pop('from_ref', None)
    #     if from_ref:
    #         try:
    #             ref = cls.get_instance(from_ref)
    #         except KeyError:
    #             raise KeyError(
    #                 f"Cannot inherit from non-existent instance: {from_ref} "
    #                 f"while creating {data.get('label', '<unknown>')}"
    #             )
    #
    #         # Check for circular inheritance
    #         if hasattr(ref, 'inheritance_chain_'):
    #             chain = ref.inheritance_chain_.copy()
    #             if from_ref in chain:
    #                 raise ValueError(
    #                     f"Circular inheritance detected: "
    #                     f"{' -> '.join(chain + [from_ref])}"
    #                 )
    #             chain.append(from_ref)
    #             data['inheritance_chain_'] = chain
    #
    #         # Copy fields from reference if not explicitly set
    #         ignored_fields = {"uid_", "label_", "digest", "from_ref"}
    #         for field_name, field_info in cls.model_fields.items():
    #             field_info: pydantic.fields.FieldInfo
    #             if (
    #                     field_name not in ignored_fields
    #                     and field_name not in data
    #                     and hasattr(ref, field_name)
    #             ):
    #                 inherited_value = getattr(ref, field_name)
    #                 if isinstance(inherited_value, (list, dict, set)):
    #                     # Deep copy mutable types
    #                     data[field_name] = copy.deepcopy(inherited_value)
    #                 else:
    #                     data[field_name] = inherited_value
    #
    #     return data
    #
    # def get_inheritance_chain(self) -> list[str]:
    #     """Return the inheritance chain for this instance"""
    #     return self.inheritance_chain_.copy()
