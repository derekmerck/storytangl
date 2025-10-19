from __future__ import annotations
import inspect
import logging
from typing import Type, Callable, Self
import weakref
from functools import partial
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from tangl.type_hints import Typelike
from tangl.core import Entity

@dataclass
class FuncInfo():
    func: Callable
    reqs_binding: bool
    takes_other: bool
    caller_cls: Typelike
    owner_cls: Typelike

    @classmethod
    def from_func(cls, func: Callable, base_cls: Typelike):

        sig = _get_func_sig(func)
        reqs_binding = _infer_reqs_binding_from_sig(sig)
        takes_other = _infer_takes_other_from_sig(sig)
        caller_cls = _infer_caller_cls_name_from_sig(sig)
        owner_cls = (_infer_owner_cls_name_from_sig(sig) or
                     _infer_owner_cls_name_from_fqn(func))

        if base_cls is not None and hasattr(base_cls, 'dereference_cls_name'):
            if isinstance(caller_cls, str):
                caller_cls = base_cls.dereference_cls_name(caller_cls) or caller_cls
            if isinstance(owner_cls, str):
                owner_cls = base_cls.dereference_cls_name(owner_cls) or owner_cls

        return cls(func, reqs_binding, takes_other, caller_cls, owner_cls)

    @classmethod
    def annotate_func(cls,
                      func: Callable,
                      base_cls: Typelike,
                      owner_cls: Typelike = None):
        info = cls.from_func(func, base_cls)
        setattr(func, "_func_info", info)

    def get_bound_func(self, func: Callable, owner: Type[Entity] = None) -> Callable:
        sig = _get_func_sig(func)

def _get_func_sig(func):
    if func is None:
        raise ValueError("func cannot be None")
    while hasattr(func, '__func__'):
        # May be a wrapped object
        func = func.__func__
    return inspect.signature(func)

def _infer_reqs_binding_from_sig(sig) -> bool:
    # This checks if the handler is defined as an instance method of a different class, if so, we have to bind it to its owner when calling
    logger.debug("Checking reqs binding")
    return bool("caller" in sig.parameters and "self" in sig.parameters)

def _infer_takes_other_from_sig(sig) -> bool:
    # This checks if we need to pass *other args into the call
    return bool("other" in sig.parameters or "others" in sig.parameters)

def _infer_caller_cls_name_from_sig(sig) -> str | None:
    logger.debug("Checking for caller_cls in sig")
    caller_param = sig.parameters.get("caller") or sig.parameters.get("self")
    if caller_param and caller_param.annotation is not inspect._empty:
        logger.debug(f"found caller class {caller_param.annotation}, {type(caller_param.annotation)}")
        # seems to always annotate with a str, but wraps deferred types with quotes as provided
        if isinstance(caller_param.annotation, str):
            return caller_param.annotation.strip('\'"')
        return caller_param.annotation

def _infer_owner_cls_name_from_sig(sig) -> str | None:
    logger.debug("Checking for owner_cls in sig")
    owner_param = sig.parameters.get("self")
    if owner_param and owner_param.annotation is not inspect._empty:
        logger.debug(f"found owner class {owner_param.annotation}, {type(owner_param.annotation)}")
        # seems to always annotate with a str, but wraps deferred types with quotes as provided

        if owner_param.annotation is Self:
            return None  # resolve it with fqn or otherwise

        if isinstance(owner_param.annotation, str):
            return owner_param.annotation.strip('\'"')
        return owner_param.annotation

def _infer_owner_cls_name_from_fqn(func) -> str | None:
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
    # so we can distinguish classes with the same name
    logger.debug(f"Checking owner class for {func.__qualname__}")
    if isinstance(func, staticmethod) or func.__name__ == "<lambda>":
        return None
    parts = func.__qualname__.split('.')
    if len(parts) < 2:
        # raise ValueError("Cannot get outer scope name for module-level func")
        return None
    maybe_cls_name = parts[-2]  # the thing before .method_name
    logger.debug(f'Parsing owner class as {maybe_cls_name}')
    return maybe_cls_name

def func_info(func: Callable, base_cls: Type[Entity] = None) -> dict:

    sig = _get_func_sig(func)
    reqs_binding = _infer_reqs_binding_from_sig(sig)
    takes_other = _infer_takes_other_from_sig(sig)
    caller_cls = _infer_caller_cls_name_from_sig(sig)
    owner_cls = (_infer_owner_cls_name_from_sig(sig) or
                 _infer_owner_cls_name_from_fqn(func))

    if base_cls is not None and hasattr(base_cls, 'dereference_cls_name'):
        if isinstance(caller_cls, str):
            caller_cls = base_cls.dereference_cls_name(caller_cls) or caller_cls
        if isinstance(owner_cls, str):
            owner_cls = base_cls.dereference_cls_name(owner_cls) or owner_cls

    return {
        'reqs_binding': reqs_binding,  # type: bool
        'takes_other': takes_other,    # type: bool
        'caller_cls': caller_cls,      # type: Type | str | None
        'owner_cls': owner_cls,        # type: Type | str | None
    }

def bind_inst_func(func: Callable, owner: Entity) -> Callable:
    # If it's an instance method on a different class, it _must_ be bound
    # to the owner as a partial.
    # Once it's bound, we no longer care about the owner.
    # Use a weakref here so a registry won't hold a zombie pointer
    _owner = weakref.proxy(owner)
    new_func = partial(func, _owner)
    new_func.__name__ = f"{func.__name__}@{owner.get_label()}"
    return func

def bind_class_func(func: Callable, owner_cls: Type[Entity]) -> Callable:
    if not isinstance(func, classmethod):
        return func
    return func.__get__(None, owner_cls)  # bind to owner_cls


class EntityPl(Entity):

    def func(self, caller: 'EntityPlPl', *others):
        ...

print( func_info(EntityPl.func, Entity) )
