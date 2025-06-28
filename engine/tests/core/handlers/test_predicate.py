import pytest

from tangl.core.entity import Entity
from tangl.core.handlers import on_gather_context, HasContext, Predicate, on_check_satisfied, Satisfiable
from tangl.utils.safe_builtins import safe_builtins

MyConditionEntity = type('MyConditionEntity', (Satisfiable, Entity), {} )


@pytest.fixture
def conditional_entity():
    yield MyConditionEntity(locals={'test_val': True}, predicates=["test_val"])


def test_conditional_entity(conditional_entity):

    context = on_gather_context.execute_all_for(conditional_entity, ctx=None)
    print(context)
    assert context['test_val'] is True

    context = conditional_entity.gather_context()
    assert context['test_val'] is True

    # It won't aggregate with check first for
    result = on_check_satisfied.execute_all_for(conditional_entity, ctx=context)
    assert result

    result = conditional_entity.is_satisfied(ctx=context)
    assert result


def test_condition_handler_builtins():
    # can access "safe builtins"
    assert Predicate.eval_raw_expr('max( [2,3] ) == 3')

    # has random
    assert 0 <= Predicate.eval_raw_expr('random()') <= 1.0

    # name error on missing items
    with pytest.raises(NameError):
        assert Predicate.eval_raw_expr('dog')

    # no access for other builtins
    with pytest.raises(NameError):
        assert Predicate.eval_raw_expr('print("hello")')

def test_complex_conditions():
    conditions = ["(x > 5 and y < 10) or z == 0"]
    namespace = {"x": 6, "y": 9, "z": 0}

    mixin = MyConditionEntity(predicates=conditions, locals=namespace)
    ctx = mixin.gather_context()
    assert mixin.is_satisfied(ctx=ctx) is True

def test_satisfied_with_no_conditions():
    node = MyConditionEntity()
    assert node.is_satisfied(ctx=None) is True

def test_syntax_error():

    node = MyConditionEntity(predicates=["x = 5"], locals={"x": 1})
    with pytest.raises(SyntaxError):
        node.is_satisfied(ctx=None)

    node = MyConditionEntity(predicates=["2 + ", "x =="])
    with pytest.raises(SyntaxError):
        node.is_satisfied(ctx=None)

def test_conditional_eval():
    result = Predicate.eval_raw_expr("2 + 2")
    assert result == 4

def test_conditional_edge_case():
    with pytest.raises(ZeroDivisionError):
        assert Predicate.eval_raw_expr("2/0")

def test_conditional_with_multiple_conditions():
    n = MyConditionEntity(locals={'abc': 'foo', 'defg': 'bar'}, predicates=["abc == 'foo'", "defg == 'bar'"])
    assert n.is_satisfied(ctx=n.gather_context())

def test_conditional_with_changing_locals():
    n = MyConditionEntity(locals={'abc': 'foo'}, predicates=["abc == 'foo'"])
    assert n.is_satisfied(ctx=n.gather_context())

    n.locals['abc'] = 'bar'
    assert not n.is_satisfied(ctx=n.gather_context())  # The condition should now fail

def test_multiple_conditions_and_changes():
    node = MyConditionEntity(predicates=["x > 0", "y == 'foo'"])

    with pytest.raises(NameError):
        assert node.is_satisfied(ctx=None)  # Variables undefined = False

    node.locals = {"x": 1, "y": "foo"}
    assert node.is_satisfied(ctx=node.gather_context())  # Variables undefined = False

    node.locals["x"] = 2
    node.locals["y"] = "bar"
    assert not node.is_satisfied(ctx=node.gather_context())  # Both conditions not satisfied

    node.locals["x"] = 0
    node.locals["y"] = "foo"
    assert not node.is_satisfied(ctx=node.gather_context())  # Both conditions not satisfied

    node.locals["x"] = 2
    node.locals["y"] = "foo"
    assert node.is_satisfied(ctx=node.gather_context())  # All conditions satisfied again

def test_conditional():

    c = MyConditionEntity( predicates=["True"] )
    assert c.is_satisfied(ctx=None)

    c = MyConditionEntity( predicates=["a == 10"], locals={'a': 10})
    assert c.is_satisfied(ctx=c.gather_context())

    c = MyConditionEntity( predicates=["a == 10"], locals={'a': 100})
    assert not c.is_satisfied(ctx=c.gather_context())

    c = MyConditionEntity( predicates=["a == 10"], locals={'b': 10})
    with pytest.raises( NameError ):
        c.is_satisfied(ctx=c.gather_context())


def test_satisfied_by():

    c = MyConditionEntity( predicates=["a == 100"] )
    v = MyConditionEntity( locals={'a': 100} )
    assert c.is_satisfied(ctx=v.gather_context())

