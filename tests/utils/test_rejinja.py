import pytest
import jinja2

from tangl.utils.rejinja import RecursiveTemplate

def test_recursive_template():
    # Create a Jinja2 environment
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)

    # Create a RecursiveTemplate instance
    template = env.from_string('{{ foo }}',
                               globals={'foo': '{{ bar }}'},
                               template_class=RecursiveTemplate)

    # Check initial state
    with pytest.raises(jinja2.exceptions.UndefinedError):
        assert template.render() == '{{ bar }}'

    # Now add 'bar' to the template globals and re-render
    template.globals['bar'] = 'Hello, world!'
    assert template.render() == 'Hello, world!'

    # Test deeper recursion
    template.globals['bar'] = '{{ baz }}'
    template.globals['baz'] = 'Deep recursion!'
    assert template.render() == 'Deep recursion!'
