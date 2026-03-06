from __future__ import annotations

from typing import Protocol


class DomainManagerProtocol(Protocol):
    def load_domain_module(self, domain_module: str) -> None: ...


class DomainCompiler:
    """Load domain modules into a domain facet/manager."""

    def load_into(self, domain_module: str, domain_manager: DomainManagerProtocol) -> None:
        domain_manager.load_domain_module(domain_module)
