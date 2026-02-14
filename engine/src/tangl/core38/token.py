"""Graph node wrappers over frozen singleton referents.

Tokens combine immutable singleton definitions with mutable node-local overlay state.
Subscribing ``Token[SomeSingleton]`` creates and caches a dynamic Pydantic wrapper class
that materializes fields marked ``instance_var=True`` as local token fields.

See Also
--------
:mod:`tangl.core38.singleton`
    Frozen referent contract and per-class singleton registries.
:mod:`tangl.core38.graph`
    ``Token`` inherits :class:`~tangl.core38.graph.Node` for graph participation.
:mod:`tangl.core38.entity`
    ``_match_fields`` metadata discovery used to materialize instance vars.
"""

# tangl/core/token.py
from __future__ import annotations

from dataclasses import dataclass
import re
import sys
import logging
from types import MethodType
from typing import Any, ClassVar, Generic, Self, Type, TypeVar

import pydantic
from pydantic import Field, PrivateAttr, field_validator, model_validator

from .graph import Node
from .singleton import Singleton

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

WST = TypeVar("WST", bound=Singleton)

class Token(Node, Generic[WST]):
    """Dynamic node wrapper around one singleton instance.

    Why
    ----
    Tokens let frozen :class:`~tangl.core38.singleton.Singleton` definitions participate
    in mutable topology. The singleton stores concept-level defaults, while each token
    stores node-local state.

    Key Features
    ------------
    - **Split identity**: ``token_from`` references the singleton label; ``label`` names
      the token node itself.
    - **Delegation + override**: reads check token fields first, then delegate missing
      attributes/methods to :attr:`reference_singleton`.
    - **Local instance vars**: singleton fields marked
      ``json_schema_extra={"instance_var": True}`` are materialized as mutable token
      fields on the generated wrapper class.
    - **Wrapper cache**: repeated ``Token[SomeType]`` subscriptions reuse the same
      cached dynamic class keyed by ``(Token, SomeType)``.

    API
    ---
    - :attr:`wrapped_cls` – singleton type bound to the dynamic token wrapper.
    - :attr:`token_from` – singleton label to resolve within :attr:`wrapped_cls`.
    - :attr:`label` – graph-node name inherited from :class:`~tangl.core38.graph.Node`.
    - :attr:`reference_singleton` – access the underlying instance.
    - :meth:`_instance_vars` – collect instance-var field definitions from the wrapped class.
    - :meth:`_create_wrapper_cls` – emit a new wrapper subclass with those fields.

    Notes
    -----
    Writes are intentionally asymmetric: instance-var fields are writable on the token,
    while delegated singleton fields remain frozen and cannot be reassigned through the
    token.

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
    """
    # Allows embedding a Singleton into a mutable node so its properties can be
    # referenced indirectly via a graph
    # Note that singletons are frozen, so the referred attributes are immutable.
    # Has a lot of python magic in it, basically just an entity from an immutable base template

    #: Cached wrapper classes keyed by (wrapper base, singleton type).
    _wrapper_cache: ClassVar[dict[tuple[type[Token], Type[Singleton]], type[Token]]] = {}

    #: The singleton entity class that this wrapper is associated with.
    wrapped_cls: ClassVar[Type[Singleton]] = None

    _registry: Any = PrivateAttr(None)

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


    @model_validator(mode="after")
    def _hydrate_instance_vars_from_referent(self) -> Self:
        """Backfill unset instance vars from the referenced singleton instance."""
        for field_name in self._instance_vars(self.wrapped_cls):
            if field_name in self.model_fields_set:
                continue
            setattr(self, field_name, getattr(self.reference_singleton, field_name))
        return self

    @property
    def reference_singleton(self) -> WST:
        res = self.wrapped_cls.get_instance(self.token_from)
        if not res:
            raise ValueError(f"No instance of `{self.wrapped_cls.__name__}` found for ref label `{self.token_from}`.")
        return res

    # conflate/delegate identity matching
    def has_kind(self, kind: Type[Node]) -> bool:
        """
        Check against wrapped type, not just Token class.

        Enables: Token[NPC].has_kind(NPC) → True
        """
        if not (isinstance(kind, type) or (isinstance(kind, tuple) and all(isinstance(k, type) for k in kind))):
            return False
        return super().has_kind(kind) or self.reference_singleton.has_kind(kind)

    def __repr__(self) -> str:
        return self.wrapped_cls.__repr__(self)

    def bind_registry(self, registry) -> None:
        """Bind registry pointer using a private dict slot on dynamic wrappers."""
        current = self.__dict__.get("_registry")
        if registry is None:
            self.__dict__["_registry"] = None
            return
        if current is not None and current is not registry:
            raise ValueError(f"Registry is already set {current!r} != {registry!r}")
        self.__dict__["_registry"] = registry

    def __getattr__(self, name: str) -> Any:
        """Delegate non-local attribute access to the referenced singleton."""
        if name == "_registry":
            return self.__dict__.get("_registry", None)
        if name.startswith("_"):
            raise AttributeError(f"{self.__class__.__name__} is missing attribute '{name}'")
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


@dataclass
class TokenFactory(Generic[WST]):
    """Provisioner-facing adapter around ``Token[WST](token_from=...)``.

    Each factory instance wraps one singleton type and exposes a tiny materialization
    API compatible with builder-like provisioner flows.
    """

    wst: Type[WST]

    def has_kind(self, kind: Type[Node]) -> bool:
        return self.wst.has_kind(kind)

    @classmethod
    def _materialize_one(cls, wrapped_cls: Type[WST], token_from: str) -> Token[WST]:
        return Token[wrapped_cls](token_from=token_from)

    def materialize_one(self, token_from: str) -> Token[WST]:
        return self._materialize_one(self.wst, token_from)
