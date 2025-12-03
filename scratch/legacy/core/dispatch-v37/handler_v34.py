# v34 handler with signature introspection
from __future__ import annotations
from typing import Generic, Callable, TypeVar, Type, Self, ClassVar, Optional, Union, TYPE_CHECKING, overload, Literal, Any
import inspect
from functools import partial, total_ordering
import logging
import weakref
from datetime import datetime, timedelta

from pydantic import field_validator, ValidationInfo, Field, PrivateAttr

from tangl.type_hints import StringMap, Typelike
from tangl.utils.dereference_obj_cls import dereference_obj_cls
from tangl.utils.summary_repr import summary_repr
from tangl.core import Entity, Registry, Singleton
from tangl.core.entity import is_identifier
from .handler import HandlerPriority

if TYPE_CHECKING:
    from .dispatch_registry import DispatchRegistry as HandlerRegistry

logger = logging.getLogger(__name__)


T = TypeVar('T')

class HandlerCallReceipt(Entity, Generic[T]):
    handler: Handler
    sort_priority: tuple[int, int, int]  # (explicit priority, mro dist, reg order)
    result: T
    ctx_delta: Optional[StringMap] = Field(None, exclude=True)

    def get_label(self):
        """<HandlerCallReceipt:my_func>"""
        label = f"{self.__class__.__name__}:{self.handler.label_ or self.handler.func.__name__}"
        return f"<{label}>"

    def summary_repr(self, max_len=20, max_items=3) -> str:
        """<h:my_func()->10>"""
        label = f"h:{self.handler.label_ or self.handler.func.__name__}"
        # we don't need to repeat caller in each one since these get layered into a service receipt for the caller, but I'll leave the empty str for consistency
        data = ''
        result = summary_repr(self.result, max_len=max_len, max_items=max_items)
        return f"<{label}({data})->{result}>"

@total_ordering
class Handler(Entity, Generic[T], arbitrary_types_allowed=True):

    func: Callable[..., T] | classmethod
    # this MUST be something that takes f(caller, *, ctx, **kwargs)

    owner_cls: Type[Entity] = None
    # This gets updated in subclass-init for decorators if using "HasHandlers" mixin
    # -- or -- we could wrap the whole class def in registration logic, but probably wouldn't
    # integrate easily with pydantic.

    @staticmethod
    def _get_func_sig(func):
        if func is None:
            raise ValueError("func cannot be None")
        while hasattr(func, '__func__'):
            func = func.__func__
        return inspect.signature(func)

    requires_binding: bool = Field(None, validate_default=True)
    @field_validator("requires_binding", mode="before")
    @classmethod
    def _infer_req_binding_from_sig(cls, data, info: ValidationInfo):
        logger.debug("Checking req binding")
        func = info.data.get("func")
        sig = cls._get_func_sig(func)
        if "caller" in sig.parameters and "self" in sig.parameters:
            requires_binding = True
        else:
            requires_binding = False
        if data is not None and requires_binding != data:
            raise ValueError(f"found discrepancy between given requires_binding {data} and sig {requires_binding}")
        return requires_binding

    takes_other: bool = Field(None, validate_default=True)  # computed/validated fields
    @field_validator("takes_other", mode="before")
    @classmethod
    def _infer_takes_other_from_sig(cls, data, info: ValidationInfo):
        logger.debug("Checking takes other")
        func = info.data.get("func")
        sig = cls._get_func_sig(func)
        if "other" in sig.parameters:
            takes_other = True
        else:
            takes_other = False
        if data is not None and takes_other != data:
            raise ValueError(f"found discrepancy between given takes_other {data} and sig {takes_other}")
        return takes_other

    takes_result: bool = Field(None, validate_default=True)
    @field_validator("takes_result", mode="before")
    @classmethod
    def _infer_takes_res_from_sig(cls, data, info: ValidationInfo):
        logger.debug("Checking takes result")
        func = info.data.get("func")
        sig = cls._get_func_sig(func)
        if "result" in sig.parameters:
            takes_result = True
        else:
            takes_result = False
        if data is not None and takes_result != data:
            raise ValueError(f"found discrepancy between given takes_result {data} and sig {takes_result}")
        return takes_result

    caller_cls_: Typelike = Field(None, validate_default=True, alias='caller_cls')
    # Can be a string initially

    @property
    def caller_cls(self) -> Type[Entity]:
        if isinstance(self.caller_cls_, str):
            self.caller_cls_ = dereference_obj_cls(Entity, self.caller_cls_)
            if self.caller_cls_ is None:
                raise TypeError(f"Failed to dereference caller class {self.caller_cls_}")
        return self.caller_cls_

    @field_validator("caller_cls_", mode="before")
    @classmethod
    def _infer_caller_cls(cls, data, info: ValidationInfo):
        if data is not None:
            logger.debug(f"provided explicit caller class {data}")
            return data
        # try to infer from sig
        func = info.data.get("func")
        maybe_cls = cls._infer_caller_cls_from_sig(func)
        if maybe_cls is not None and maybe_cls != "Self":
            return maybe_cls
        # try to infer from fqn
        # todo: should do this ONLY if caller param _not_ in sig but self is or caller cls is "Self"
        maybe_cls = cls._infer_owner_cls_from_fqn(func)
        if maybe_cls is not None:
            return maybe_cls
        raise ValueError("Cannot infer calling class for handler, provide an explicit 'caller_cls' param or an annotation on 'caller' param in func sig")

    @classmethod
    def _infer_caller_cls_from_sig(cls, func):
        logger.debug("Checking for caller_cls in sig")
        sig = cls._get_func_sig(func)
        caller_param = sig.parameters.get("caller") or sig.parameters.get("self")
        if caller_param and caller_param.annotation is not inspect._empty:
            logger.debug(f"found caller class {caller_param.annotation}, {type(caller_param.annotation)}")
            # seems to always annotate with a str, but wraps deferred types with quotes as provided
            if isinstance(caller_param.annotation, str):
                return caller_param.annotation.strip('\'"')
            return caller_param.annotation

    @classmethod
    def _infer_owner_cls_from_fqn(cls, func):
        """
        Lazily determine the actual class that owns this handler
        if it was not explicitly specified at creation time.

        Instance methods, for example, can be inferred by parsing
        ``func.__qualname__`` to get the immediate parent class name,
        then dereferencing that name in the Tangl entity hierarchy.

        :return: The class object representing the method's owner, or None
                 if it's a staticmethod/lambda.
        :rtype: Optional[Type[Entity]]
        """
        # todo: requires a fixing -- distinguish classes with the same name
        #       e.g., "MyTestEntity" by looking for module.class instead of just class name
        # so we can distinguish classes wtih the same name
        logger.debug(f"Checking owner class for {func.__qualname__}")
        if not isinstance(func, staticmethod) and not func.__name__ == "<lambda>":
        # if not isinstance(func, (classmethod, staticmethod)) and not func.__name__ == "<lambda>":
            parts = func.__qualname__.split('.')
            if len(parts) < 2:
                # raise ValueError("Cannot get outer scope name for module-level func")
                return None
            maybe_cls_name = parts[-2]  # the thing before .method_name
            logger.debug(f'Parsing owner class as {maybe_cls_name}')
            return maybe_cls_name

    caller_criteria: StringMap = Field(default_factory=dict)

    def matches_caller(self, caller: Entity) -> bool:
        return caller.matches(has_cls=self.caller_cls, **self.caller_criteria)

    # managed by the registrar, used for priority and to control for single registration
    registration_order: int = -1

    def bind_to(self, owner: Entity) -> Self:
        # If it's an instance method on a different class, it _must_ be bound to the owner
        # as a partial.
        # Once it's bound, we no longer care about the owner.
        if not self.requires_binding:
            raise RuntimeError("not an owner-bound method, cannot bind owner")
        # Use a weakref here so a registry won't hold a zombie pointer
        _owner = weakref.proxy(owner)
        new_func = partial(self.func, _owner)
        label = f"{self.func.__name__}@{owner.label}"

        logger.debug("Checking caller criteria")
        if Self not in self.caller_criteria.values():
            cc = self.caller_criteria
        else:
            cc = {}
            for k, v in self.caller_criteria.items():
                if v is Self:
                    logger.debug("Found self in criteria")
                    cc[k] = owner
                else:
                    cc[k] = v

        h_bound = self.model_copy(
            update={'func': new_func,
                    'label_': label,
                    'caller_criteria': cc,
                    'requires_binding': False})
        return h_bound

    def __call__(self, caller: Entity, *, ctx: StringMap | None, other: Entity = None, result: T = None) -> HandlerCallReceipt[T]:
        if self.requires_binding:
            raise RuntimeError("cannot call owner-bound method handler without binding owner")
        kwargs = {}
        if self.takes_other:
            kwargs["other"] = other
        elif other is not None:
            raise ValueError("handler sig does not accept 'other' entity kwarg")
        if self.takes_result:
            kwargs['result'] = result
        elif result is not None:
            raise ValueError("handler sig does not accept 'result' entity kwarg")

        if isinstance(self.func, classmethod):
            func = self.func.__get__(None, self.owner_cls)  # bind to owner_cls
        else:
            func = self.func

        result = func(caller, ctx=ctx, **kwargs)
        receipt = HandlerCallReceipt(handler=self,
                                     sort_priority=self.sort_key(caller),
                                     result=result)
        return receipt

    @classmethod
    def define(cls, *, registry: HandlerRegistry = None, bind_to: Entity = None, **kwargs):
        """Decorator"""
        def dec(func: Callable) -> Callable:
            # Unwrap
            h = cls(func=func, **kwargs)
            setattr(func, "_handler", h)
            if registry is not None:
                if not h.requires_binding:
                    registry.add(h)
                elif bind_to is not None:
                    # Have a registry, requires binding, and indicated bind_to param
                    h = h.bind_to(bind_to)
                    registry.add(h)
                else:
                    # since we need to bind the owner on init, we can stash the registry
                    # with the func
                    setattr(func, "_handler_registry", registry)
            return func
        return dec

    def has_func_name(self, name: str) -> bool:
        return name == self.func.__name__

    @identifier_property
    def label(self) -> str:
        return self.label_ or self.func.__name__

    ### ORDERING ###

    priority: int = HandlerPriority.NORMAL

    def sort_key(self, caller: Entity = None):

        # Cannot infer relative mro distance without a reference caller
        if caller is None:
            return self.priority, self.registration_order

        def mro_dist(sub_cls, super_cls):
            """Return MRO index: 0 for direct match, 1 for parent, etc. Large for unrelated."""
            try:
                return sub_cls.__class__.mro().index(super_cls)
            except ValueError:
                return 999  # Arbitrarily large if not in hierarchy

        return (self.priority,
                mro_dist(caller, self.owner_cls),
                self.registration_order)

    def __lt__(self, other: Self):
        return self.sort_key() < other.sort_key()

    def __hash__(self) -> int:
        # delegate hash, assuming each func can only correspond to a single handler
        return hash(self.func)
