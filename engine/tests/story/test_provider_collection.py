"""Focused tests for story provider collection helpers."""

from __future__ import annotations

from tangl.core import Singleton, TokenCatalog
from tangl.story.provider_collection import collect_token_catalogs


class _TokenSingleton(Singleton):
    pass


def test_collect_token_catalogs_dedupes_repeated_catalogs() -> None:
    catalog = TokenCatalog(wst=_TokenSingleton)

    class _Provider:
        def get_token_catalogs(self, *, caller=None, requirement=None, graph=None):
            return [catalog, catalog]

    catalogs = collect_token_catalogs([_Provider()], caller=object())

    assert catalogs == [catalog]
