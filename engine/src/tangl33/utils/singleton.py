from typing import ClassVar, Self

class Singleton:

    instance: ClassVar = None

    @classmethod
    def get_instance(cls) -> Self:
        if not cls.instance:
            cls.instance = cls()
        return cls.instance

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls.instance is not None:
            raise RuntimeError(f"Use {cls.__name__}.get_instance instead")
        return super().__new__(cls)
