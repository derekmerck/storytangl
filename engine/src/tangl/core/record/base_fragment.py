# tangl/core/record/base_fragment.py
from typing import Optional, Literal
import typing
from enum import Enum

from pydantic import Field, ConfigDict, model_serializer

from tangl.type_hints import UnstructuredData
from .record import Record

# note:
# BaseFragment stays in core as the minimal narrative/UI record envelope.
# Derived fragment types (text/media/group/control, etc.) should live with the
# journal/story layer (e.g. `tangl.journal`), not in core.

class BaseFragment(Record):
    # language=rst
    """
    BaseFragment(fragment_type: str | Enum | None = None)

    Minimal envelope for narrative/UI fragments emitted during resolution.

    Why
    ----
    Journal output is a linear stream of immutable fragments. This base class
    supplies the common schema so domains can emit text/media/control updates in a
    uniform way, while the client layer decides how to render them.

    Key Features
    ------------
    * **Record-derived** – immutable, globally sequenced, tag/channel-filterable
      via :class:`Record` and :class:`StreamRegistry`.
    * **Client-facing type** – :attr:`fragment_type` (e.g., ``"text"``,
      ``"media"``, ``"kv"``, ``"group"``, ``"control"``) tells the
      *presentation layer* how to interpret the payload once serialized to JSON.
    * **Extensible payload** – higher-level fragment types
      (:class:`ContentFragment`, :class:`ControlFragment`,
      :class:`GroupFragment`, :class:`KvFragment`, media fragments, etc.)
      add their own fields but share this envelope.

    API
    ---
    - :attr:`fragment_type` – enum/str indicating display/processing semantics
      at the client boundary.

    Notes
    -----
    Fragments form the **Journal** (non-replayable UX) as distinct from
    **Events** or **Patches** (replayable state changes). Use :attr:`origin_id`
    and :meth:`Record.origin` to trace a fragment back to originating graph
    entities or handlers.

    The engine routes fragments by concrete Python type and tags (e.g.,
    ``is_instance=BaseFragment`` with ``has_channel="journal"``). The
    :attr:`fragment_type` field exists primarily for clients that only see the
    JSON representation and need a cheap discriminator for rendering logic.
    """
    model_config = ConfigDict(extra='allow')

    fragment_type: str
    # intent for fragment, e.g., 'content', 'update', 'group', 'media', etc.
    # `See tangl.journal`, required if creating a bare BaseFragment

    def model_dump(self, **kwargs) -> UnstructuredData:
        # Fragment-type will often be default b/c it's basically a class var.
        data = super().model_dump(**kwargs)
        data['fragment_type'] = self.fragment_type
        return data

    # @model_serializer(mode='wrap')
    # def include_literals(self, next_serializer):
    #     dumped = next_serializer(self)
    #     for name, field_info in self.model_fields.items():
    #         if typing.get_origin(field_info.annotation) == typing.Literal:
    #             dumped[name] = getattr(self, name)
    #     return dumped
