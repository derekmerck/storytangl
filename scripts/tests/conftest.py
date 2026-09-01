"""Put the helper scripts on the path; they are scripts, not an installed package."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture(autouse=True)
def refuse_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep default script tests offline even when a worker is configured."""

    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("scripts/tests must not make network requests")

    monkeypatch.setattr(requests.sessions.Session, "request", fail)
