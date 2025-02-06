import importlib

import os
from pathlib import Path

import pytest


def test_conf():

    # reads config files
    import tangl.config
    from tangl.config import settings
    assert str(settings.service.paths.docs).endswith("docs/_build")

    with pytest.raises(AttributeError):
        assert settings.my_var == "bar"

    with pytest.raises(AttributeError):
        assert settings.service.hello == "mars"

    # env overrides work
    os.environ['TANGL_MY_VAR'] = "jupiter"
    os.environ['TANGL_SERVICE__HELLO'] = "mars"
    assert os.environ['TANGL_SERVICE__HELLO'] == "mars"

    importlib.reload(tangl.config)
    from tangl.config import settings

    assert settings.my_var == "jupiter"
    assert str(settings.service.paths.docs).endswith("docs/_build")
    assert settings.service.hello == "mars"


if __name__ == "__main__":
    test_conf()
