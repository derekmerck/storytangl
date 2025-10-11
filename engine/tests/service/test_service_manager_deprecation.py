from __future__ import annotations

import pytest

from tangl.service.service_manager import ServiceManager


def test_service_manager_emits_deprecation_warning():
    with pytest.warns(DeprecationWarning):
        ServiceManager()
