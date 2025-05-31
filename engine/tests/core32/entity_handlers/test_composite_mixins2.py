import pytest

from tangl.core import Entity, HasContext, on_gather_context, Renderable, on_render, HasConditions, on_check_conditions


class MyEntity(HasConditions, Renderable, HasContext, Entity):

    @on_gather_context.register()
    def _mock_data(self, **context) -> dict:
        return {'abc': 'foo'}

    @on_render.register()
    def _mock_render(self, **context) -> dict:
        s = self.render_str("this should say 'foo': {{ abc }}", **context)
        return {'content': s}

    @on_check_conditions.register()
    def _mock_conditions(self, **context) -> list:
        return [ "abc == 'foo'" ]

@pytest.fixture
def entity():
    return MyEntity()


def test_ns(entity):
    ns = entity.gather_context()
    assert ns['abc'] == 'foo'


def test_render(entity):
    res = entity.render()
    assert res['content'] == "this should say 'foo': foo"

@pytest.mark.xfail(reason="still not sure exactly how this gets used")
def test_conditions(entity):
    res = entity.check_conditions()
    assert res


