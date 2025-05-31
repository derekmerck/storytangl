from typing import Any, Self, Type
import logging

from pydantic import BaseModel, field_validator, field_serializer, FieldValidationInfo

logger = logging.getLogger(__name__)

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

    def reset_fields(self):
        """
        Reset flagged entity fields to their default state.

        To flag a field for reset, set `json_schema_extra={reset_field: True}` .
        """
        for field_name, field_info in self.model_fields.items():
            extra = field_info.json_schema_extra or {}
            if extra.get('reset_field', False):
                default_value = field_info.get_default(call_default_factory=True)
                logger.debug(f"updating: {field_name} = {default_value}")
                setattr(self, field_name, default_value)

    # There is no built-in method for excluding fields from comparison with pydantic.
    # For this approach, set json_schema_extra = {'cmp', false} on fields to ignore.
    # Other approaches include unlinking fields during comparison then relinking them, or
    # comparing model_dumps with excluded fields.

    @classmethod
    def cmp_fields(cls):
        return [k for k, f in cls.model_fields.items()
                if not f.json_schema_extra or f.json_schema_extra.get("cmp", True)]

    def __eq__(self, other: Self) -> bool:
        if self.__class__ is not other.__class__:
            return False
        for field in self.cmp_fields():
            if getattr(self, field) != getattr(other, field):
                return False
        return True

    @classmethod
    def _pydantic_field_type_is(cls, field_name: str, query_type: Type):
        # Get the field's annotation from the model
        field_type = cls.model_fields[field_name].annotation
        # Support typing generics
        origin = getattr(field_type, '__origin__', None)
        if field_type is query_type or origin is query_type:
            return True
        return False

