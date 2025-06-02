from __future__ import annotations
from typing import ClassVar

import pytest
from pydantic import BaseModel

from legacy.utils.property_hints import get_property_return_hints, get_return_hint

class TestPropClass(BaseModel):

    not_a_property: ClassVar[str] = None

    @property
    def discrete_prop(self) -> BaseModel:
        ...

    @property
    def list_prop(self) -> list[TestPropClass]:
        ...

def test_property_hint_errs(capsys):

    with pytest.raises((AttributeError, NameError),):
        get_return_hint(TestPropClass.not_a_property)

    class TestPropClass2(TestPropClass):
        @property
        def foo(self) -> 'Bar':
            ...

    with pytest.raises((AttributeError, NameError),):
        get_property_return_hints(TestPropClass2)
        assert "Cannot infer type from foo" in capsys.readouterr().err


def test_property_hints():

    hints = get_property_return_hints(TestPropClass)
    print( hints )

    assert hints == {'discrete_prop': ('discrete', BaseModel), 'list_prop': ('collection', TestPropClass)}