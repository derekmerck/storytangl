import pytest

from tangl.core.entity import Entity
from tangl.core.handler import HasContext, on_gather_context, Satisfiable, on_check_satisfied

# todo: extend to rendering

class MyEntity2(Satisfiable, Entity):

    @on_gather_context.register()
    def _mock_data(self, ctx) -> dict:
        return {'abc': 'foo'}

    # @on_render_content.register()
    # def _mock_render(self, **context) -> dict:
    #     s = self.render_str("this should say 'foo': {{ abc }}", **context)
    #     return {'content': s}

    @on_check_satisfied.register()
    def _mock_conditions(self, ctx) -> list:
        return [ "abc == 'foo'" ]


@pytest.fixture
def entity():
    return MyEntity2()


def test_ns(entity):
    ns = entity.gather_context()
    assert ns['abc'] == 'foo'


# def test_render(entity):
#     res = entity.render()
#     assert res['content'] == "this should say 'foo': foo"


def test_conditions(entity):
    res = entity.is_satisfied(ctx=entity.gather_context())
    assert res


