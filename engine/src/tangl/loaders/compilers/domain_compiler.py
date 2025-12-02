from __future__ import annotations

from tangl.story.fabula.domain_manager import DomainManager


class DomainCompiler:
    """Load domain modules into a :class:`DomainManager`."""

    def load_into(self, domain_module: str, domain_manager: DomainManager) -> None:
        domain_manager.load_domain_module(domain_module)
