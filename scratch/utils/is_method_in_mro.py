from types import MethodType

def is_method_in_mro(func: callable, cls: type) -> bool:
    if isinstance(func, MethodType):
        func = func.__func__

    found = any(
        (func in C.__dict__.values()) or
        (isinstance(v, (classmethod, staticmethod)) and v.__func__ == func)
        for C in cls.__mro__
        for v in C.__dict__.values()
    )
    if found:
        return True

    # For SingletonNodes, it may further be a method on the wrapped class
    if hasattr(cls, 'wrapped_cls'):
        return is_method_in_mro(func, cls.wrapped_cls)

    return False
