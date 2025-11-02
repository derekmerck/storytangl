"""Helpers for resolving domain-specific classes within a story world."""
from __future__ import annotations
from typing import Optional, Type
import importlib
import inspect
import logging

from tangl.core.behavior import BehaviorRegistry
from tangl.core.entity import Entity
from tangl.core.graph.node import Node

logger = logging.getLogger(__name__)

# todo: TypeManager?
class DomainManager:
    """DomainManager()

    Lookup helper that maps script-provided class names to runtime types.

    Why
    ---
    Story scripts describe nodes using symbolic ``obj_cls`` strings. The
    :class:`DomainManager` resolves those strings to actual Python classes so the
    runtime can instantiate nodes, handlers, or other extensibility points.

    Key Features
    ------------
    * **Custom registry** – ``register_class`` adds friendly aliases such as
      ``"Elf"`` → :class:`Elf`.
    * **Import fallback** – ``resolve_class`` attempts module-qualified imports
      when a name is not registered locally.
    * **Graceful default** – falls back to :class:`~tangl.core.graph.node.Node`
      when a class cannot be resolved.

    API
    ---
    - :meth:`register_class` – register aliases.
    - :meth:`resolve_class` – resolve script values.
    - :meth:`load_domain_module` – bulk-register subclasses from a module.
    - :attr:`dispatch_registry` – :class:`~tangl.core.dispatch.BehaviorRegistry`
      for domain handlers.
    """

    def __init__(self) -> None:
        self.class_registry: dict[str, Type[Entity]] = {}
        self.dispatch_registry = BehaviorRegistry(label="domain_handlers")

    def register_class(self, name: str, cls: Type[Entity]) -> None:
        """Register ``name`` as an alias for ``cls``."""
        self.class_registry[name] = cls

    def resolve_class(self, obj_cls_str: Optional[str]) -> Type[Entity]:
        """Resolve ``obj_cls_str`` to a concrete class."""
        if not obj_cls_str:
            return Node

        if obj_cls_str in self.class_registry:
            return self.class_registry[obj_cls_str]

        try:
            module_path, class_name = obj_cls_str.rsplit(".", 1)
        except ValueError:
            logger.warning("Could not resolve %s; using Node fallback.", obj_cls_str)
            return Node

        try:
            module = importlib.import_module(module_path)
            resolved = getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            logger.warning("Failed to import %s (%s); using Node fallback.", obj_cls_str, exc)
            return Node

        if inspect.isclass(resolved):
            if issubclass(resolved, Entity):
                return resolved

            logger.warning(
                "Resolved class %s is not an Entity subclass; using Node fallback.",
                obj_cls_str,
            )
            return Node

        logger.warning("Resolved object %s is not a class; using Node fallback.", obj_cls_str)
        return Node

    def load_domain_module(self, module_path: str) -> None:
        """Import ``module_path`` and register discovered :class:`Entity` subclasses."""
        module = importlib.import_module(module_path)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Entity) and obj is not Entity:
                self.register_class(name, obj)
