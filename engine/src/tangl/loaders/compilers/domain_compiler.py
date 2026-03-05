from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tangl.story.fabula.domain_manager import DomainManager


class DomainCompiler:
    """Load domain modules into a :class:`DomainManager`."""

    def load_into(self, domain_module: str, domain_manager: DomainManager) -> None:
        domain_manager.load_domain_module(domain_module)
