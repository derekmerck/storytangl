import pytest

from tangl.core.entity import Entity
from tangl.core.handlers import HasConditions, on_check_conditions, on_gather_context

MyConditionEntity = type('MyConditionEntity', (HasConditions, Entity), {} )


@pytest.fixture
def conditional_entity():
    yield MyConditionEntity(locals={'test_val': True}, conditions=["test_val"])


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


def test_condition_handler_builtins():
    r = MyConditionEntity()

    # can access "safe builtins"
    assert 0 <= r.eval_expr('random()') <= 1.0
    assert r.eval_expr('max( [2,3] ) == 3')

    # no access for other builtins
    with pytest.raises(NameError):
        assert r.eval_expr('print("hello")')

def test_complex_conditions():
    conditions = ["(x > 5 and y < 10) or z == 0"]
    namespace = {"x": 6, "y": 9, "z": 0}

    mixin = MyConditionEntity(conditions=conditions, locals=namespace)
    assert mixin.check_conditions() is True

def test_satisfied_with_no_conditions():
    node = MyConditionEntity(conditions=[])
    assert node.check_conditions() is True

def test_syntax_error():

    node = MyConditionEntity(conditions=["x = 5"], locals={"x": 1})
    with pytest.raises(SyntaxError):
        node.check_conditions()

    node = MyConditionEntity(conditions=["2 + ", "x =="])
    with pytest.raises(SyntaxError):
        node.check_conditions()

def test_conditional_eval():
    result = MyConditionEntity.eval_expr("2 + 2")
    assert result == 4

def test_conditional_edge_case():
    with pytest.raises(ZeroDivisionError):
        assert MyConditionEntity.eval_expr("2/0")

def test_conditional_with_multiple_conditions():
    n = MyConditionEntity(locals={'abc': 'foo', 'defg': 'bar'}, conditions=["abc == 'foo'", "defg == 'bar'"])
    assert n.check_conditions()

def test_conditional_with_changing_locals():
    n = MyConditionEntity(locals={'abc': 'foo'}, conditions=["abc == 'foo'"])
    assert n.check_conditions()

    n.locals['abc'] = 'bar'
    assert not n.check_conditions()  # The condition should now fail

def test_multiple_conditions_and_changes():
    node = MyConditionEntity(conditions=["x > 0", "y == 'foo'"])

    with pytest.raises(NameError):
        assert node.check_conditions()  # Variables undefined = False

    node.locals = {"x": 1, "y": "foo"}
    assert node.check_conditions()  # Variables undefined = False

    node.locals["x"] = 2
    node.locals["y"] = "bar"
    assert not node.check_conditions()  # Both conditions not satisfied

    node.locals["x"] = 0
    node.locals["y"] = "foo"
    assert not node.check_conditions()  # Both conditions not satisfied

    node.locals["x"] = 2
    node.locals["y"] = "foo"
    assert node.check_conditions()  # All conditions satisfied again

def test_conditional():

    c = MyConditionEntity( conditions=["True"] )
    assert c.check_conditions()

    c = MyConditionEntity( conditions=["a == 10"], locals={'a': 10})
    assert c.check_conditions()

    c = MyConditionEntity( conditions=["a == 10"], locals={'a': 100})
    assert not c.check_conditions()

    c = MyConditionEntity( conditions=["a == 10"], locals={'b': 10})
    with pytest.raises( NameError ):
        c.check_conditions()


def test_satisfied_by():

    c = MyConditionEntity( conditions=["a == 100"] )
    v = MyConditionEntity( locals={'a': 100} )
    assert c.check_satisfied_by(v)

