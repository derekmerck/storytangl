# tangl/core/record/base_fragment.py
from typing import Optional, Literal
from enum import Enum

from pydantic import Field, ConfigDict

from .record import Record

# red, output, linked within by red, without by yellow

class BaseFragment(Record, extra='allow'):
    # language=rst
    """
    BaseFragment(fragment_type: str)

    Minimal envelope for narrative/UI fragments emitted during resolution.

    Why
    ----
    Journal output is a linear stream of immutable fragments. This base class
    supplies the common schema so domains can emit text/media/control updates in a
    uniform way.

    Key Features
    ------------
    * **Record-derived** – immutable, sequenced, channel-filterable.
    * **Typed** – :attr:`fragment_type` (e.g., `text`, `media`, `kv`, `group`, `control`).
    * **Extensible** – higher-level fragment types (:class:`Content<ContentFragment>`/:class:`Control<ControlFragment>`/:class:`Group<GroupFragment>`/:class:`KV<KvFragment>`) add
      their own content schema but share the same envelope.

    API
    ---
    - :attr:`fragment_type` – enum/str indicating display/processing semantics.

    Notes
    -----
    Fragments form the **Journal** (non-replayable UX) as distinct from **Events**
    (replayable ops). Use origin links to trace a fragment back to originating
    graph entities or handlers.
    """
    model_config = ConfigDict(extra='allow')

    fragment_type: Optional[ str | Enum ] = None
    # intent for fragment, e.g., 'content', 'update', 'group', 'media', etc.  `See tangl.journal`
