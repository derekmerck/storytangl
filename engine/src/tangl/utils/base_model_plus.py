# tangl/utils/base_model_plus.py
from functools import total_ordering
from typing import Any, Self, Type, Iterator, ClassVar, TypeVar, get_args, get_origin, Union
import logging
from uuid import uuid4
from inspect import isclass

from pydantic import BaseModel, field_validator, field_serializer, model_serializer, FieldValidationInfo, model_validator, Field


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class BaseModelPlus(BaseModel):

    # SET HANDLING

    @field_validator('*', mode='before')
    @classmethod
    def _cast_to_set(cls, v, info: FieldValidationInfo):
        # Only process if this is a set-typed field
        if cls._pydantic_field_type_is(info.field_name, set):
            if v is None:
                return set()
            if isinstance(v, str):
                return {x.strip() for x in v.split(',')}
        return v

    @model_serializer(mode='wrap')
    def _convert_sets_to_list(self, nxt_ser):
        dumped = nxt_ser(self)
        for k in dumped.keys():
            if isinstance(dumped[k], set):
                dumped[k] = list(dumped[k])
        return dumped

    # @field_serializer('*', mode='wrap')
    # def _convert_set_to_list(self, values: set, nxt_ser):
    #     if isinstance(values, set) and values:
    #         return list(values)
    #     return nxt_ser(values)
    #     # return values

    # GENERICS

    @classmethod
    def get_generic_types_for(
        cls,
        generic_cls: Type | None = None,
        *,
        include_pydantic_metadata: bool = True,
    ) -> tuple[type, ...]:
        """Return the concrete type arguments used for a generic base.

        This is designed to work with both standard `typing` generics and
        Pydantic v2's specialized generic models.

        Args:
            generic_cls:
                If provided, only return args for the matching generic origin
                (e.g., `Template`, `Registry`, `HierarchicalTemplate`).
                If omitted and multiple generic bases exist, a ValueError is raised.
            include_pydantic_metadata:
                If True, consult `__pydantic_generic_metadata__` on `cls` and its
                MRO. This is required for Pydantic v2 generic specializations.

        Returns:
            A tuple of concrete type arguments (may be empty if none found).

        Raises:
            ValueError: if `generic_cls` is None and the class has multiple generic
                bases with discoverable type parameters.
        """

        def _matches(origin: object, target: Type | None) -> bool:
            if target is None:
                return True
            if origin is target:
                return True
            if isclass(origin) and isclass(target) and issubclass(origin, target):
                return True
            return False

        results: list[tuple[type, ...]] = []

        # 1) Pydantic v2: concrete generic args live in __pydantic_generic_metadata__.
        if include_pydantic_metadata:
            for t in cls.mro():
                meta = getattr(t, "__pydantic_generic_metadata__", None)
                if not meta:
                    continue
                origin = meta.get("origin")
                args = meta.get("args") or ()
                if origin is None:
                    continue
                if _matches(origin, generic_cls) and args:
                    # unwrap TypeVars -> bound, when possible
                    concrete: list[type] = []
                    for a in args:
                        if isinstance(a, TypeVar):
                            if a.__bound__ is not None:
                                concrete.append(a.__bound__)
                            else:
                                # Unbound TypeVar: treat as Any-ish; keep as object
                                # but preserve type-ness for callers
                                continue
                        else:
                            concrete.append(a)
                    if concrete:
                        results.append(tuple(concrete))

        # 2) Standard typing generics: inspect __orig_bases__ across the MRO.
        for t in cls.mro():
            for base in getattr(t, "__orig_bases__", ()):
                origin = get_origin(base)
                if origin is None:
                    continue
                if not _matches(origin, generic_cls):
                    continue
                args = get_args(base)
                if args:
                    concrete: list[type] = []
                    for a in args:
                        if isinstance(a, TypeVar):
                            if a.__bound__ is not None:
                                concrete.append(a.__bound__)
                            else:
                                continue
                        else:
                            concrete.append(a)
                    if concrete:
                        results.append(tuple(concrete))

        # No matches.
        if not results:
            return ()

        # If disambiguated, return the first hit (MRO-ordered).
        if generic_cls is not None:
            return results[0]

        # Otherwise ensure uniqueness.
        uniq = list(dict.fromkeys(results))
        if len(uniq) != 1:
            raise ValueError(
                f"Ambiguous generic bases for {cls.__name__}; "
                f"pass generic_cls=... to disambiguate. Found: {uniq}"
            )
        return uniq[0]

    @classmethod
    def get_generic_type_for(
        cls,
        generic_cls: Type,
        index: int = 0,
        *,
        default: type | None = None,
    ) -> type | None:
        """Convenience: return a single generic arg at `index` for `generic_cls`."""
        args = cls.get_generic_types_for(generic_cls)
        if not args:
            return default
        try:
            return args[index]
        except IndexError:
            return default

    # INTROSPECTION

    @classmethod
    def public_fields(cls) -> list[str]:
        """Returns a list of constructor parameter names or aliases, if an alias is defined."""
        field_names = [ f.alias if f.alias else k for k, f in cls.model_fields.items() ]
        return field_names

    @classmethod
    def _fields(cls, as_field=False, **criteria) -> Iterator[Union[Field, str]]:
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
                if as_field:
                    yield f
                else:
                    yield n
            else:
                logger.debug(f"Skipping field: {n}")

    # There is no built-in method for excluding fields from comparison with pydantic.
    # For this approach, set json_schema_extra = {'compare', False} on fields to ignore.
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

    # def __str__(self):
    #     data = self.model_dump()
    #     s = yaml.dump(data, default_flow_style=False)
    #     return s

    def evolve(self, **kwargs) -> Self:
        """Create an updated copy of this model."""
        # This does NOT validate the update attribs
        kwargs['uid'] = uuid4()
        return self.model_copy(update=kwargs, deep=True)

    def update_attrs(self, force=False, **kwargs):
        """
        Update attributes of this model in place.

        Use `force=True` to update attributes on a frozen instance by
        editing the underlying dict directly (be careful!)
        """
        for k, v in kwargs.items():
            if hasattr(self, k):
                if force:
                    self.__dict__[k] = v
                else:
                    setattr(self, k, v)

    @classmethod
    def __fqn__(cls):
        return f"{cls.__module__}.{cls.__name__}"

    @classmethod
    def dereference_cls_name(cls, name: str) -> Type[Self]:
        # Call on upper bound
        # todo: Should memo-ize this
        logger.debug(f"dereferenceing {name} on cls {cls.__qualname__} with fqn {cls.__fqn__()}")
        if name == cls.__qualname__ or name == cls.__fqn__():
            return cls
        for _cls in cls.__subclasses__():
            if x := _cls.dereference_cls_name(name):
                return x


@total_ordering
class HasSeq(BaseModel):
    # This is a helper mixin for total orderings

    seq: int = Field(init=False)  # type checking, ignore missing

    @model_validator(mode="before")
    @classmethod
    def _set_seq(cls, data):
        data = dict(data or {})
        if data.get('seq') is None:  # unassigned or passed none
            # Only incr if not already set
            data['seq'] = cls.incr_count()
        return data

    # start at -1 since we increment before returning the first value, which should be 0
    _instance_count: ClassVar[int] = -1

    @classmethod
    def _reset_instance_count(cls):
        cls._instance_count = -1

    # Currently keeping seq across _all_ records of all types from all domains
    # def __init_subclass__(cls, **kwargs):
    #     cls._instance_count = 0  # keep an instance counter per subclass
    #     super().__init_subclass__()

    @classmethod
    def incr_count(cls) -> int:
        cls._instance_count += 1
        return cls._instance_count

    def __lt__(self, other):
        # Default __lt__ sorts non-seq to the front without raising
        # Override as necessary in subclasses that want a custom ordering
        return self.seq < getattr(other, 'seq', -1)
