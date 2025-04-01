import pytest

from tangl.core.handlers import on_check_conditions, HasConditions, on_gather_context

@pytest.fixture
def conditional_entity():
    yield HasConditions(locals={'test_val': True}, conditions=["test_val"])


def test_conditional_entity(conditional_entity):

    context = on_gather_context.execute(conditional_entity)
    assert context == {'test_val': True}

    context = conditional_entity.gather_context()
    assert context == {'test_val': True}

    result = on_check_conditions.execute(conditional_entity, **context)
    assert result

    result = conditional_entity.check_conditions()
    assert result

    result = on_check_conditions.execute(conditional_entity, test_val=False)
    assert not result

