from __future__ import annotations
import pytest
from typing import List, Dict, Union, Any, Callable, Optional

from legacy.utils.compare_ftypes import compare_ftypes
import pytest

class A:
    pass

class B(A):
    pass

class C:
    pass


class D:
    # should accept
    def baseline(self: A, var, **kwargs) -> C:
        pass

    # should accept
    def matching_forward_refs(self: 'A', var, **kwargs) -> 'C':
        pass

    # should reject (wrong v0 arg)
    def wrong_class_forward_refs(self: 'D', var, **kwargs) -> 'C':
        pass

    # should reject (not enough args)
    def missing_args_forward_refs(self: 'A', **kwargs) -> 'C':
        pass


def pattern_func(this: A, var1, var2=None, **kwargs) -> C:
    pass

def test_accepts_baseline():
    assert compare_ftypes(pattern_func, pattern_func) is True

    def exact_match(this: A, var1, var2=None, **kwargs) -> C: ...
    assert compare_ftypes(pattern_func, exact_match) is True

def test_accepts_v0_subclass():

    # arg0 as a subclass is ok
    def subclass_var0(this: B, var3, var4=None, **kwargs) -> C:
        pass

    assert compare_ftypes(pattern_func, subclass_var0) is True

def test_accepts_no_annotations():
    # lack of annotations is ok
    def unannotated(this, var1, var2=None, **kwargs):
        pass

    assert compare_ftypes(pattern_func, unannotated) is True

def test_accepts_missing_kwargs():

    # missing kwargs is ok
    def missing_kwargs(this: A, var1, **kwargs) -> C:
        pass
    assert compare_ftypes(pattern_func, missing_kwargs) is True

def test_accepts_extra_kwargs():

    # extra kwargs is ok
    def extra_kwargs(this: A, var1, var2=None, var3=None, **kwargs) -> C:
        pass
    assert compare_ftypes(pattern_func, extra_kwargs) is True

def test_rejects_wrong_v0():

    # wrong first var type
    def wrong_v0(this: C, var6, **kwargs) -> C:
        pass

    assert compare_ftypes(pattern_func, wrong_v0) is False

def test_rejects_wrong_ret():

    # wrong return type
    def wrong_ret(this: A, var6, **kwargs) -> int:
        pass

    assert compare_ftypes(pattern_func, wrong_ret) is False

def test_rejects_too_many_vars():
    # too many positional args
    def too_many_vars(this: A, var6, var7, **kwargs) -> C:
        pass

    assert compare_ftypes(pattern_func, too_many_vars) is False

def test_rejects_not_enough_vars():

    # not enough positional args
    def missing_vars(this: A, **kwargs) -> C:
        pass

    assert compare_ftypes(pattern_func, missing_vars) is False

def test_no_kwargs():
    def no_kwargs(this: A, var1, var2):
        pass
    assert compare_ftypes(pattern_func, no_kwargs) is False


def test_accepts_baseline_forward_ref_methods():
    assert compare_ftypes(pattern_func, D.baseline) is True

def test_accepts_matching_forward_ref_methods():
    assert compare_ftypes(pattern_func, D.matching_forward_refs) is True

def test_rejects_wrong_class_forward_ref_methods():
    assert compare_ftypes(pattern_func, D.wrong_class_forward_refs) is False

def test_rejects_missing_args_forward_ref_methods():
    assert compare_ftypes(pattern_func, D.missing_args_forward_refs) is False
