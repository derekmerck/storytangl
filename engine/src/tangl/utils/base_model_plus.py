from typing import Any, Self, Type, Iterator
import logging

import yaml
from pydantic import BaseModel, field_validator, field_serializer, FieldValidationInfo
from pydantic.fields import FieldInfo

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class BaseModelPlus(BaseModel):

    # SET HANDLING

    @field_validator('*', mode='before')
    @classmethod
    def _cast_to_set(cls, v, info: FieldValidationInfo):
        # Only process if this is a set-typed field
        if cls._pydantic_field_type_is(info.field_name, set):
            if isinstance(v, str):
                return {x.strip() for x in v.split(',')}
            if v is None:
                return set()
        return v

    @field_serializer('*')
    def _convert_set_to_list(self, values: set):
        if isinstance(values, set):
            return list(values)
        return values

    # INTROSPECTION

    @classmethod
    def public_fields(cls) -> list[str]:
        """Returns a list of constructor parameter names or aliases, if an alias is defined."""
        field_names = [ f.alias if f.alias else k for k, f in cls.model_fields.items() ]
        return field_names

    @classmethod
    def _fields(cls, **criteria) -> Iterator[str]:
        """
        Returns fields with attribs or json_extra metadata keys = values.

        By default, we infer opt-out metadata flags, "don't use me for something".
        If you want an opt-in or other field comparison, set the constraint value to a tuple
        with the (target value, default value).

        That is, use `_field(k=(t,f), ...)` to indicate the target value and default value,
        if the default is not True.
        """
        def matches(field, **criteria):
            for k, v in criteria.items():
                if isinstance(v, tuple):
                    v, default_annotation = v
                else:
                    default_annotation = True
                extra = field.json_schema_extra or {}
                # Check for both field.key or json_extra[key] or use default
                if hasattr(field, k):
                    annotation = getattr(field, k, None)
                else:
                    annotation = extra.get(k, None)
                if annotation is None:
                    annotation = default_annotation
                if annotation != v:
                    logger.debug(f'{k} => {annotation} != {v}')
                    return False
            return True

        for n, f in cls.model_fields.items():
            if matches(f, **criteria):
                logger.debug(f"Including field: {n}")
                yield n
            else:
                logger.debug(f"Skipping field: {n}")

    # There is no built-in method for excluding fields from comparison with pydantic.
    # For this approach, set json_schema_extra = {'cmp', false} on fields to ignore.
    # Other approaches include unlinking fields during comparison then relinking them, or
    # comparing model_dumps with excluded fields.
    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        # Not marked as compare=False (opt-out), and not exclude=True (opt-in)
        for f in self._fields(compare=True, exclude=(False, False)):
            if getattr(self, f) != getattr(other, f):
                return False
        return True

    def reset_fields(self):
        """
        Reset flagged entity fields to their default state.
        To flag a field for reset, set `json_schema_extra={reset_field: True}` .
        """
        for field in self._fields(reset=(True, False)):
            field_info = self.model_fields[field]
            default_value = field_info.get_default(call_default_factory=True)
            logger.debug(f"updating: {field} = {default_value}")
            setattr(self, field, default_value)

    @classmethod
    def _pydantic_field_type_is(cls, field_name: str, query_type: Type):
        # Get the field's annotation from the model
        field_type = cls.model_fields[field_name].annotation
        # Support typing generics
        origin = getattr(field_type, '__origin__', None)
        if field_type is query_type or origin is query_type:
            return True
        return False

    def __str__(self):
        data = self.model_dump()
        s = yaml.dump(data, default_flow_style=False)
        return s
