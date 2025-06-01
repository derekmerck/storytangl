import pytest

from tangl.core.entity import Entity
from tangl.core.handler import HasContext, context_handler, Satisfiable, availability_handler

# todo: extend to rendering

class MyEntity(HasContext, Satisfiable, Entity):

    @context_handler.register()
    def _mock_data(self, ctx) -> dict:
        return {'abc': 'foo'}

    # @render_handler.register()
    # def _mock_render(self, **context) -> dict:
    #     s = self.render_str("this should say 'foo': {{ abc }}", **context)
    #     return {'content': s}

    @availability_handler.register()
    def _mock_conditions(self, ctx) -> list:
        return [ "abc == 'foo'" ]


@pytest.fixture
def entity():
    return MyEntity()


def test_ns(entity):
    ns = entity.gather_context()
    assert ns['abc'] == 'foo'


# def test_render(entity):
#     res = entity.render()
#     assert res['content'] == "this should say 'foo': foo"


def test_conditions(entity):
    res = entity.is_satisfied(ctx=entity.gather_context())
    assert res


