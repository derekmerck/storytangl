import os

import pytest
from dynaconf import Dynaconf


def test_conf(monkeypatch: pytest.MonkeyPatch) -> None:

    # reads config files
    import tangl.config

    tangl.config.show_settings()

    from tangl.config import settings
    assert str(settings.service.paths.docs).endswith("docs/build/html")

    with pytest.raises(AttributeError):
        assert settings.my_var == "bar"

    with pytest.raises(AttributeError):
        assert settings.service.hello == "mars"

    # env overrides work
    monkeypatch.setenv('TANGL_MY_VAR', "jupiter")
    monkeypatch.setenv('TANGL_SERVICE__HELLO', "mars")
    assert os.environ['TANGL_SERVICE__HELLO'] == "mars"

    settings = Dynaconf(envvar_prefix="TANGL", preload=[tangl.config.default_settings])

    assert settings.my_var == "jupiter"
    assert str(settings.service.paths.docs).endswith("docs/build/html")
    assert settings.service.hello == "mars"
