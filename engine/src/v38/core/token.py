# tangl/core/token.py
from __future__ import annotations
import re
from types import MethodType
from typing import TypeVar, Generic, ClassVar, Type, Self, Any
import sys
import logging

import pydantic
from pydantic import Field, field_validator

from .entity import Entity
from .singleton import Singleton

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

WST = TypeVar("WST", bound=Singleton)

class Token(Entity, Generic[WST]):
    """
    Token[Singleton](from_ref: UniqueStr)

    Graph node wrapper that attaches a :class:`~tangl.core.Singleton` to a graph with node-local state.  Tokens are mid-way between templates and node-instances.  They delegate most features to a bound singleton reference object but provide a layer of instance-local state on top of that.

    Why
    ----
    Let immutable singletons participate in topology while allowing per-node state (e.g.,
    position, runtime flags) that does not mutate the singleton itself.

    Key Features
    ------------
    * **Binding** – :attr:`wrapped_cls` points to the singleton class; :attr:`label` selects instance.
    * **Delegation** – attribute access defers to the wrapped singleton; methods are rebound for convenience.
    * **Instance vars** – singleton fields marked ``json_schema_extra={"instance_var": True}``
      are materialized on the node for local override.
    * **Dynamic wrappers** – :meth:`__class_getitem__` / :meth:`_create_wrapper_cls` generate typed wrappers on demand.

    API
    ---
    - :attr:`wrapped_cls` – singleton type bound to this wrapper.
    - :attr:`label` – required label of the referenced instance; validated at creation.
    - :attr:`reference_singleton` – access the underlying instance.
    - :meth:`_instance_vars` – collect instance-var field definitions from the wrapped class.
    - :meth:`_create_wrapper_cls` – emit a new wrapper subclass with those fields.

    Notes
    -----
    Prefer modeling behavior in the singleton; keep node-local overrides minimal and explicit.

    Token factory uses generic typing: `Token[SingletonType](token_from=foo)`

    Examples:
        >>> class SwordType(Singleton):
        ...    damage: str
        ...    sharpness: float = Field(1.0, json_schema_extra={"instance_var": True})
        ...    def __repr__(self):
        ...        return ( f"<{self.__class__.__name__}:{self.get_label()}"
        ...                 f"(damage={self.damage}, sharpness={self.sharpness})>" )
        >>> SwordType(label="short sword", damage="1d6")
        <SwordType:short sword(damage=1d6, sharpness=1.0)>
        >>> t = Token[SwordType](token_from="short sword",
        ...                      label="Glamdring", sharpness=2.0); t
        <Token[...SwordType]:Glamdring(damage=1d6, sharpness=2.0)>
        >>> t.has_kind(SwordType)
        True
        >>> t.sharpness -= 0.5; t  # used it, mutate instance var
        <Token[...SwordType]:Glamdring(damage=1d6, sharpness=1.5)>
        >>> SwordType.get_instance("short sword").sharpness  # reference unchanged
        1.0

    class that masquerades as a Singleton template object with an overlay for local/dynamic vars and refers others to base class

    This is almost always going to be mixed with GraphItem and used by a graph to materialize and link a 'platonic' singleton as a concrete node.  Singleton type might be 'weapon' and inst might be 'sword'.  A sword token delegates methods and attributes to its reference singleton, but adds a local 'sharpness' variable.

    - Fields on the ref_kind annotated with 'local_field' will be added to the token on class creation and the field value on the ref_inst used for the default value on token construction
    - Other field references will be delegated to the ref directly.

    - If you invalidate the reference singleton (by clearing for example), all associated
      tokens will be unable to resolve their referent unless they are already holding a
      cached reference, in which case the reference singleton can _not_ be garbage
      colleccted.  Use cautiously.
    """
    # Allows embedding a Singleton into a mutable node so its properties can be
    # referenced indirectly via a graph
    # Note that singletons are frozen, so the referred attributes are immutable.
    # Has a lot of python magic in it, basically just an entity from an immutable base template

    #: Cached wrapper classes keyed by (wrapper base, singleton type).
    _wrapper_cache: ClassVar[dict[tuple[type[Token], Type[Singleton]], type[Token]]] = {}

    #: The singleton entity class that this wrapper is associated with.
    wrapped_cls: ClassVar[Type[Singleton]] = None

    token_from: str = Field(...)

    # todo: why is this commented out, probably _do_ want to be able to update tags
    #       maybe b/c discarding would be hard?  (i.e., keep {-foo} and use it to
    #       hide {foo}?)  Probably want something like this anyway for other complete
    #       tag-merging purposes.
    # tags: set[Tag] = Field(default_factory=set, json_schema_extra={"instance_var": True})

    # noinspection PyNestedDecorators
    @field_validator("token_from")
    @classmethod
    def _valid_label_for_wrapped_cls(cls, value: str) -> str:
        if not cls.wrapped_cls.has_instance(value):
            raise ValueError(f"No instance of `{cls.wrapped_cls.__name__}` found for ref label `{value}`.")
        return value

    @property
    def reference_singleton(self) -> WST:
        res = self.wrapped_cls.get_instance(self.token_from)
        if not res:
            raise ValueError(f"No instance of `{self.wrapped_cls.__name__}` found for ref label `{self.token_from}`.")
        return self.wrapped_cls.get_instance(self.token_from)

    # conflate/delegate identity matching
    def has_kind(self, kind: Type[Entity]) -> bool:
        """
        Check against wrapped type, not just Token class.

        Enables: Token[NPC].has_kind(NPC) → True
        """
        return super().has_kind(kind) or self.reference_singleton.has_kind(kind)

    def __repr__(self) -> str:
        return self.wrapped_cls.__repr__(self)

    def __getattr__(self, name: str) -> Any:
        """Delegates attribute access to non-instance-variables back to the reference singleton entity."""
        # logger.debug(f"Getting attribute {name}")
        if hasattr(self.reference_singleton, name):
            attr = getattr(self.reference_singleton, name)
            # logger.debug(f"Delegating {name} attribute to {attr}")
            if callable(attr):
                # If it's a method, bind it to the reference_entity
                # This only works with instance methods that take 'self' 1st param, see Wearable
                return MethodType(attr.__func__, self)
                # return functools.partial(attr, self)
            return attr
        raise AttributeError(f"{self.__class__.__name__} is missing attribute '{name}'")

    @classmethod
    def _instance_vars(cls, wrapped_cls: Type[WST] = None):
        inst_fields = list(wrapped_cls._match_fields(instance_var=True))
        return {
            name: (info.annotation, info)
            for name, info in wrapped_cls.model_fields.items() if name in inst_fields
        }

    @classmethod
    def _create_wrapper_cls(cls, wrapped_cls: Type[WST], name: str = None) -> Type[Self]:
        """Class method to dynamically create a new wrapper class given a reference singleton type."""
        cache_key = (cls, wrapped_cls)
        if cache_key in cls._wrapper_cache:
            return cls._wrapper_cache[cache_key]

        module = sys.modules[__name__]
        if name is None:
            qualname = f"{wrapped_cls.__module__}.{wrapped_cls.__qualname__}"
            sanitized = re.sub(r"[^0-9a-zA-Z_]", "_", qualname)
            name = f"{cls.__name__}[{sanitized}]"

        instance_vars = cls._instance_vars(wrapped_cls)
        generic_metadata = {'origin': cls, 'args': (wrapped_cls,), 'parameters': ()}

        logger.debug(f"Creating new wrapper class {name} for {wrapped_cls.__name__}")

        new_cls = pydantic.create_model(name,
                                        __base__=cls,
                                        __module__=module.__name__,
                                        **instance_vars)
        setattr(new_cls, "wrapped_cls", wrapped_cls)
        setattr(new_cls, "__pydantic_generic_metadata__", generic_metadata)

        # Adding the ephemeral class to this module's namespace allows them to be pickled and cached
        setattr(module, name, new_cls)
        cls._wrapper_cache[cache_key] = new_cls

        return new_cls

    @classmethod
    def __class_getitem__(cls, wrapped_cls: Type[WST]) -> Type[Self]:
        """
        Unfortunately difficult to use pydantic's native Generic handling with this b/c we
        want to manipulate the fields as the model is created.
        """
        if isinstance(wrapped_cls, TypeVar):
            # Sometimes we want to use a type var
            wrapped_cls = wrapped_cls.__bound__
        return cls._create_wrapper_cls(wrapped_cls)
