from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.presentation.hints import PresentationHints
from tangl.vm import TraversableNode


class Block(TraversableNode):
    """Block()

    Primary interactive cursor node in a runtime story graph.

    Why
    ----
    Blocks are the units a player or consumer actually visits. They hold the
    authored narrative content together with local role, setting, and media
    declarations that journaling and provisioning consume.

    Key Features
    ------------
    * Carries authored prose in ``content``.
    * Connects to Actions wired from the owning world template.
    * Declares local roles, settings, and media used by namespace and render
      handlers.

    API
    ---
    - :attr:`content` stores authored narrative text, and :attr:`content_hints`
      how a client is meant to read it, carried on its content fragment.
    - :attr:`roles`, :attr:`settings`, and :attr:`media` hold local provider and
      presentation declarations.
    """

    content: str = ""
    content_hints: PresentationHints | None = None
    roles: list[dict[str, Any]] = Field(default_factory=list)
    settings: list[dict[str, Any]] = Field(default_factory=list)
    media: list[dict[str, Any]] = Field(default_factory=list)
    action_name: str = ""
    is_anonymous: bool = False

    @property
    def _is_anonymous(self) -> bool:
        """Compatibility alias for authored anonymous-block provenance."""
        return self.is_anonymous
