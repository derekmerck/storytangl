# tangl.core.fragment.presentation_hints.py
from __future__ import annotations
from typing import Optional, Any
import functools

from pydantic import BaseModel, Field, ConfigDict

from tangl.type_hints import StyleId, StyleClass, StyleDict

class PresentationHints(BaseModel, extra="allow"):
    """
    Advisory styling metadata for fragments.

    Why
    ----
    Lets producers suggest how a client might present a fragment without binding
    behavior. Clients may ignore hints; they are best-effort guidance.

    Key Features
    ------------
    * **Stable & frozen** – immutable model for auditability.
    * **Common fields** – :attr:`style_name`, :attr:`style_tags`, :attr:`style_dict`, :attr:`icon`.
    * **Clean serialization** – :meth:`model_dump` sets `by_alias=True` and `exclude_none=True`.

    API
    ---
    - :attr:`style_name` – suggested presentation id / CSS id.
    - :attr:`style_tags` – list of tags / CSS classes.
    - :attr:`style_dict` – key-value styles (e.g., `{"color": "#333"}`).
    - :attr:`icon` – optional icon hint.

    Notes
    -----
    You can encode lightweight semantics in tags (e.g., `portrait`, `from_right`,
    `2.0s`). For richer media semantics, add domain-specific hint models.
    """
    model_config = ConfigDict(frozen=True)

    style_name: Optional[StyleId] = None
    style_tags: Optional[list[StyleClass]] = Field(default_factory=list)
    style_dict: Optional[StyleDict] = Field(default_factory=dict)
    icon: Optional[str] = None

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('by_alias', True)
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(*args, **kwargs)

    # todo: should have an inference from tags like ["color=blue", ...] -> {'color': 'blue'}
