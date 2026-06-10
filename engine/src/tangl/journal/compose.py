# tangl/journal/compose.py
"""Blessed stanzas for ``compose_journal`` handlers.

Why
---
Post-merge composition handlers keep re-inventing the same three moves:
replace one fragment in place, reorder a merged batch into a deliberate
telling, and bind the result together as a retrievable unit. This module
names those moves once so mechanics and world domain modules compose beats
instead of hand-rolling fragment loops.

API
---
- :func:`replace_first` — swap the first fragment matching a predicate.
- :func:`assemble_slots` — order fragments into named syuzhet slots.
- :func:`beat_overlay` — emit a ``GroupFragment`` binding a composed beat.

See Also
--------
:doc:`docs/src/design/story/JOURNAL_COMPOSE_CONTRACT.md`
    Transform contract and placement boundary for composition handlers.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence

from tangl.core import Record

from .fragments import GroupFragment

REST_SLOT = "*"
"""Slot name standing for every fragment the classifier left unassigned."""


def replace_first(
    fragments: Iterable[Record],
    match: Callable[[Record], bool],
    replacement: Record,
    *,
    insert_missing: bool = False,
) -> list[Record]:
    """Return a new batch with the first fragment matching ``match`` replaced.

    Later matches pass through unchanged. When nothing matches and
    ``insert_missing`` is set, ``replacement`` is prepended instead.
    """
    composed: list[Record] = []
    replaced = False
    for fragment in fragments:
        if not replaced and match(fragment):
            composed.append(replacement)
            replaced = True
            continue
        composed.append(fragment)
    if not replaced and insert_missing:
        composed.insert(0, replacement)
    return composed


def assemble_slots(
    fragments: Iterable[Record],
    *,
    order: Sequence[str],
    classify: Callable[[Record], str | None],
) -> list[Record]:
    """Order fragments into the named slots of a deliberate telling.

    ``classify`` maps each fragment to a slot name; fragments mapped to a
    name absent from ``order`` (or to ``None``) collect in the rest pool,
    emitted where ``order`` places :data:`REST_SLOT` (appended at the end
    when ``order`` omits it). Relative order within a slot is preserved.
    """
    slots: dict[str, list[Record]] = {name: [] for name in order if name != REST_SLOT}
    rest: list[Record] = []
    for fragment in fragments:
        slot = classify(fragment)
        if slot is not None and slot in slots:
            slots[slot].append(fragment)
        else:
            rest.append(fragment)

    composed: list[Record] = []
    for name in order:
        composed.extend(rest if name == REST_SLOT else slots[name])
    if REST_SLOT not in order:
        composed.extend(rest)
    return composed


def beat_overlay(
    members: Sequence[Record],
    *,
    beat: str,
    group_type: str = "beat",
    **metadata: Any,
) -> GroupFragment:
    """Bind composed fragments into a retrievable beat overlay.

    The overlay travels as a peer fragment: clients that understand groups can
    present or retrieve the beat as a unit, and segmentation-aware retrieval
    can slice on ``group_type``/``content`` without re-deriving membership.
    """
    return GroupFragment(
        group_type=group_type,
        content=beat,
        member_ids=[fragment.uid for fragment in members],
        **metadata,
    )


__all__ = ["REST_SLOT", "assemble_slots", "beat_overlay", "replace_first"]
