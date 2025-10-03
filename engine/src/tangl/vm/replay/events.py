# tangl/vm/replay/events.py
from __future__ import annotations
from enum import Enum
from uuid import UUID
from typing import Any, Iterable, Optional, Literal, Self
from copy import deepcopy
import logging

from pydantic import Field

from tangl.core import Entity, Record, Registry

logger = logging.getLogger(__name__)


class EventType(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    def apply_order(self) -> int:
        _ORDER = {self.DELETE: 0,
                  self.CREATE: 1,
                  self.UPDATE: 2,
                  self.READ: 3}
        return _ORDER[self]

class Event(Record):
    # Records b/c they are persisted, structured, unstructured
    record_type: Literal['event'] = 'event'
    event_type: EventType = Field(...)

    source_id: UUID = Field(...)
    name: Optional[str] = None  # attrib name for update
    value: Any = Field(...)
    old_value: Any | None = None

    def apply(self, registry: Registry) -> None:
        if not isinstance(registry, Registry):
            raise TypeError("Event.apply should be called directly on a Registry")
        if self.source_id == registry.uid:
            source = registry
        else:
            source = registry.get(self.source_id)  # type: Entity

        match self.event_type:
            case EventType.CREATE:
                if not isinstance(self.value, Entity):
                    value = Entity.structure(self.value)
                else:
                    value = self.value
                source.add(value)
            case EventType.READ:
                # Non-mutating
                pass
            case EventType.UPDATE:
                setattr(source, self.name, self.value)
            case EventType.DELETE:
                # slightly obtuse, but probably rarely used
                # if it has a _name_ it's a delattr,
                # if it has a _value_, it's a remove item
                if self.name is not None:
                    delattr(source, self.name)
                elif self.value is not None:
                    source.remove(self.value)
                else:
                    raise ValueError("Must have a attrib name or a value-key for remove")

    # todo: this should get pulled out and switched by a flag in patch, perhaps with other
    #       patch representations, like dict-diff and no wrapped/observed object for comparison.
    @classmethod
    def canonicalize_events(cls, events: Iterable[Event]) -> Iterable[Event]:
        """
        Canonicalize a patch's events under these per-node rules (same uid):
          - Starts with CREATE:
              C                  -> keep LAST C
              C D                -> ∅
              C D C              -> keep LAST C
              C D C D            -> ∅
          - Starts with DELETE:
              D                  -> keep FIRST D
              D C                -> keep FIRST D, LAST C
              D C D              -> keep FIRST D
              D C D C            -> keep FIRST D, LAST C
          - Updates:
              • Drop all updates on nodes whose final existence is False (no kept CREATE).
              • If there is a kept CREATE, drop (truncate) all updates at or before the last kept CREATE.
              • After truncation, coalesce multiple UPDATE/attr-DELETE on the same (uid, name) to the last one.
          - Reads are dropped.
        The final ordering is DELETE < CREATE < UPDATE < READ with original causal order as a tiebreaker.
        """
        from collections import defaultdict

        # 0) Preserve causal order via (seq or input index)
        enumerated = list(enumerate(events))
        # Original causal index for tie-breaking later
        orig_index = {id(e): i for i, e in enumerated}
        ordered = sorted(enumerated, key=lambda ie: (getattr(ie[1], "seq", ie[0])))

        def _uid_from_create(ev: Event) -> Optional[UUID]:
            if isinstance(ev.value, Entity):
                return ev.value.uid
            if isinstance(ev.value, dict) and "uid" in ev.value:
                return ev.value["uid"]
            return None

        def _uid_from_node_delete(ev: Event) -> Optional[UUID]:
            val = ev.value
            if isinstance(val, UUID):
                return val
            if hasattr(val, "uid"):
                return getattr(val, "uid")
            if isinstance(val, dict) and "uid" in val:
                return val["uid"]
            return None

        # 1) Collect structural ops per uid
        create_idx: dict[UUID, list[int]] = defaultdict(list)
        delete_idx: dict[UUID, list[int]] = defaultdict(list)
        for idx, e in ordered:
            if e.event_type is EventType.CREATE:
                uid = _uid_from_create(e)
                if uid is not None:
                    create_idx[uid].append(idx)
            elif e.event_type is EventType.DELETE and e.name is None and e.value is not None:
                uid = _uid_from_node_delete(e)
                if uid is not None:
                    delete_idx[uid].append(idx)

        # 2) Decide which structural endpoints to keep per uid
        keep_struct_indices: set[int] = set()
        last_kept_create_idx: dict[UUID, int] = {}
        final_exists: dict[UUID, bool] = {}

        all_uids = set(create_idx.keys()) | set(delete_idx.keys())
        for uid in all_uids:
            c_list = create_idx.get(uid, [])
            d_list = delete_idx.get(uid, [])
            if not c_list and not d_list:
                continue

            first_c = c_list[0] if c_list else None
            first_d = d_list[0] if d_list else None
            starts_with_delete = first_d is not None and (first_c is None or first_d < first_c)

            last_is_create = bool(c_list) and (not d_list or c_list[-1] > d_list[-1])

            if starts_with_delete:
                # keep FIRST D; and keep LAST C if sequence ends in C
                if first_d is not None:
                    keep_struct_indices.add(first_d)
                if last_is_create:
                    keep_struct_indices.add(c_list[-1])
                    last_kept_create_idx[uid] = c_list[-1]
                    final_exists[uid] = True
                else:
                    final_exists[uid] = False
            else:
                # starts with CREATE
                if last_is_create:
                    # keep only LAST C
                    keep_struct_indices.add(c_list[-1])
                    last_kept_create_idx[uid] = c_list[-1]
                    final_exists[uid] = True
                else:
                    # C ... D  -> ∅
                    final_exists[uid] = False

        # 3) Walk events; keep structural endpoints and filtered/coalesced attribute mutations
        kept: list[Event] = []
        last_attr_event: dict[tuple[UUID, str], Event] = {}

        for idx, e in ordered:
            # Node DELETE (encoded: name=None, value=uid/item)
            if e.event_type is EventType.DELETE and e.name is None and e.value is not None:
                uid = _uid_from_node_delete(e)
                if uid is None:
                    # If we can't resolve a uid, keep the event conservatively
                    kept.append(e)
                elif idx in keep_struct_indices:
                    kept.append(e)
                # else drop
                continue

            if e.event_type is EventType.CREATE:
                uid = _uid_from_create(e)
                if uid is None:
                    kept.append(e)
                elif idx in keep_struct_indices:
                    kept.append(e)
                # else drop
                continue

            # Attribute-level mutations
            if e.event_type in (EventType.UPDATE, EventType.DELETE) and e.name:
                uid = e.source_id
                # Drop if node does not exist in the final state
                if uid in final_exists and not final_exists[uid]:
                    continue
                # Drop if this mutation occurs at or before the last kept CREATE
                lkc = last_kept_create_idx.get(uid, None)
                if lkc is not None and idx <= lkc:
                    continue
                key = (uid, e.name)
                # Coalesce: last one wins
                last_attr_event[key] = e
                continue

            # READ or other non-mutating: drop READs
            if e.event_type is EventType.READ:
                continue

            # Unknown / conservative keep
            kept.append(e)

        # 4) Merge in the coalesced attribute-level events
        kept.extend(last_attr_event.values())

        # 5) Final stable ordering: DELETE < CREATE < UPDATE < READ, then causal order
        type_rank = {
            EventType.DELETE: 0,
            EventType.CREATE: 1,
            EventType.UPDATE: 2,
            EventType.READ:   3,
        }
        kept.sort(key=lambda ev: (type_rank.get(ev.event_type, 99), orig_index.get(id(ev), 10**9)))
        logger.debug(f"From {len(enumerated)} source events, kept: {len(kept)} canonical events")
        return kept

    @classmethod
    def apply_all(cls, events: Iterable[Self], registry: Registry) -> Registry:
        # assumes canonicalized events
        # returns an _updated copy_ of the source
        if not isinstance(registry, Registry):
            raise TypeError("Event replay should be called directly on a Registry")
        _registry = deepcopy(registry)
        for event in events:
            event.apply(_registry)
        return _registry


