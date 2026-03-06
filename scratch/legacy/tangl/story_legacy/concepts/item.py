from __future__ import annotations

from typing import ClassVar

from tangl.core import Graph

from .concept import Concept


class Item(Concept):
    """Item(label: str)

    Inventory element tracked as a concept node.

    Why
    ---
    Games and interactive fiction often model items as entities that can be
    referenced by multiple nodes. ``Item`` wraps that pattern in a lightweight
    concept so stories can gate branches on possession and apply scripted
    effects when items are acquired or consumed.

    Key Features
    ------------
    * **Graph resident** – instances live in the story graph and can be
      discovered with :meth:`Graph.find_nodes`.
    * **Acquisition helpers** – :meth:`acquire` and :meth:`consume` mutate the
      node's ``acquired`` tag.
    * **Predicate helpers** – :meth:`has_item` checks acquisition state for use
      inside scripted expressions.
    """

    ACQUIRED_TAG: ClassVar[str] = "acquired"

    name: str | None = None
    description: str = ""
    consumable: bool = False

    @classmethod
    def acquire(cls, item_label: str, *, graph: Graph) -> "Item":
        """Mark ``item_label`` as acquired within ``graph``.

        Raises
        ------
        ValueError
            If the requested item does not exist in ``graph``.
        """

        item = cls._locate(item_label, graph=graph)
        item.tags.add(cls.ACQUIRED_TAG)
        return item

    @classmethod
    def consume(cls, item_label: str, *, graph: Graph) -> "Item":
        """Remove the acquisition tag from ``item_label`` if present."""

        item = cls._locate(item_label, graph=graph)
        item.tags.discard(cls.ACQUIRED_TAG)
        return item

    @classmethod
    def has_item(cls, item_label: str, *, graph: Graph) -> bool:
        """Return ``True`` when ``item_label`` has been acquired."""

        item = graph.find_one(label=item_label, is_instance=cls)
        return bool(item and item.has_tags(cls.ACQUIRED_TAG))

    @classmethod
    def _locate(cls, item_label: str, *, graph: Graph) -> "Item":
        item = graph.find_one(label=item_label, is_instance=cls)
        if item is None:
            raise ValueError(f"Item '{item_label}' not found in graph")
        return item


class Flag(Concept):
    """Flag(label: str)

    Narrative state flag represented as a graph concept.

    Why
    ---
    Flags model boolean story facts that other nodes can query. Keeping them in
    the graph allows effects and conditions to reference a shared entity
    instead of juggling ad-hoc globals.

    Key Features
    ------------
    * **Boolean state** – :attr:`active` toggles when flags are raised or
      cleared.
    * **Helpers for scripts** – :meth:`activate`, :meth:`deactivate`, and
      :meth:`is_active` are designed for use inside story expressions.
    """

    description: str = ""
    active: bool = False

    @classmethod
    def activate(cls, flag_label: str, *, graph: Graph) -> "Flag":
        """Set ``flag_label`` to active."""

        flag = cls._locate(flag_label, graph=graph)
        flag.active = True
        return flag

    @classmethod
    def deactivate(cls, flag_label: str, *, graph: Graph) -> "Flag":
        """Set ``flag_label`` to inactive."""

        flag = cls._locate(flag_label, graph=graph)
        flag.active = False
        return flag

    @classmethod
    def is_active(cls, flag_label: str, *, graph: Graph) -> bool:
        """Return ``True`` when ``flag_label`` is active."""

        flag = graph.find_one(label=flag_label, is_instance=cls)
        return bool(flag and flag.active)

    @classmethod
    def _locate(cls, flag_label: str, *, graph: Graph) -> "Flag":
        flag = graph.find_one(label=flag_label, is_instance=cls)
        if flag is None:
            raise ValueError(f"Flag '{flag_label}' not found in graph")
        return flag
