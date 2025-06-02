import pytest
from legacy.utils.is_method_in_mro import is_method_in_mro

class BaseClass:
    def base_method(self):
        pass

    @classmethod
    def base_class_method(cls):
        pass

    @staticmethod
    def base_static_method():
        pass

class SubClass(BaseClass):
    def sub_method(self):
        pass

    @classmethod
    def sub_class_method(cls):
        pass

    @staticmethod
    def sub_static_method():
        pass

def test_instance_method():
    assert is_method_in_mro(SubClass.sub_method, SubClass)
    assert is_method_in_mro(SubClass().sub_method, SubClass)
    assert not is_method_in_mro(SubClass.sub_method, BaseClass)

def test_class_method():
    assert is_method_in_mro(SubClass.sub_class_method, SubClass)
    assert is_method_in_mro(SubClass().sub_class_method, SubClass)

def test_static_method():
    assert is_method_in_mro(SubClass.sub_static_method, SubClass)

def test_inherited_method():
    assert is_method_in_mro(SubClass.base_method, SubClass)
    assert is_method_in_mro(SubClass().base_method, SubClass)
    assert is_method_in_mro(BaseClass.base_method, SubClass)

def test_inherited_class_method():
    assert is_method_in_mro(SubClass.base_class_method, SubClass)
    assert is_method_in_mro(SubClass().base_class_method, SubClass)

def test_inherited_static_method():
    assert is_method_in_mro(SubClass.base_static_method, SubClass)

def test_method_not_in_mro():
    class UnrelatedClass:
        def unrelated_method(self):
            pass

    assert not is_method_in_mro(UnrelatedClass.unrelated_method, SubClass)

def test_function_not_in_mro():
    def standalone_function():
        pass

    assert not is_method_in_mro(standalone_function, SubClass)

def test_method_comparison_with_different_bound_instances():
    instance1 = SubClass()
    instance2 = SubClass()
    assert is_method_in_mro(instance1.sub_method, SubClass)
    assert is_method_in_mro(instance2.sub_method, SubClass)

def test_method_from_multiple_inheritance():
    class MixinClass:
        def mixin_method(self):
            pass

    class MultipleInheritanceClass(SubClass, MixinClass):
        pass

    assert is_method_in_mro(MultipleInheritanceClass.mixin_method, MultipleInheritanceClass)
    assert not is_method_in_mro(MultipleInheritanceClass.mixin_method, SubClass)