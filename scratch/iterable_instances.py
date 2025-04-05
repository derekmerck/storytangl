from typing import Iterator, Self

from pydantic._internal._model_construction import ModelMetaclass

class IterableInstances(type):

    # Iterators belong in the _metaclass_
    def __iter__(self):
        return self.__class_iter__()


class IterableInstancesMixin(metaclass=IterableInstances):

    @classmethod
    def __class_iter__(cls) -> Iterator[Self]:
        if hasattr(cls, '_instances'):
            return iter(cls._instances.values())

IterableInstancesModel = type("IterableInstancesModel", (IterableInstances, ModelMetaclass), {})
