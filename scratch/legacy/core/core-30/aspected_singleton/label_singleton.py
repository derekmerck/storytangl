from __future__ import annotations
from typing import ClassVar, Self
import logging
import functools

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel, Identifier
from .singleton import Singleton

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class LabelSingleton(Singleton, BaseModel):
    """
    LabelSingletons use their label as an implicit secret for a digest.
    """
    # Use a indirect/private label to allow for pydantic mixin with Entity,
    # which provides optional and dynamic label assignment
    label_: UniqueLabel = Field(..., alias='label', min_length=1)

    @property
    def label(self) -> UniqueLabel:
        return self.label_

    _instances_by_label: ClassVar[dict[str, Self]] = {}

    @classmethod
    def __init_subclass__(cls, **kwargs):
        if cls.__dict__.get("_instances_by_label") is None:
            cls._instances_by_label = dict()
        super().__init_subclass__(**kwargs)

    @classmethod
    def compute_digest(cls, *, label: str, **kwargs) -> bytes:
        # This will not work for deferred digests since label will be
        # aliased from "label_", but since a label is required at init,
        # that shouldn't ever happen.
        secret = str((cls.__name__, label), )
        digest = cls.hash_value(secret)
        logger.debug(f"label digest: {digest}")
        return digest

    @classmethod
    def register_instance(cls, instance: Self):
        logger.debug("Registering label instance")
        if instance.label in cls._instances:
            raise KeyError(f"Duplicate key {instance.label} in {cls.__name__}")
        cls._instances_by_label[instance.label] = instance
        logger.debug(f"Instance {instance.label} registered by label")
        super().register_instance(instance)

    @classmethod
    def get_instance(cls, key: Identifier, **kwargs) -> Self:
        return cls._instances_by_label.get(key) or super().get_instance(key, **kwargs)

    @classmethod
    def has_instance(cls, key: Identifier, **kwargs) -> Self:
        return key in cls._instances_by_label or super().has_instance(key, **kwargs)

    @classmethod
    def clear_instances(cls, **kwargs):
        cls._instances_by_label.clear()
        super().clear_instances(**kwargs)

    @classmethod
    def unregister_instance(cls, instance: Self):
        if instance.label in cls._instances_by_label:
            del cls._instances_by_label[instance.label]
        super().unregister_instance(instance)

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs):
        """
        Singleton entities can be serialized by reference since they are immutable
        with respect to their public interface.
        """
        return {
            'obj_cls': self.__class__,
            'label': self.label
        }

    def __repr__(self):
        return f"<{self.__class__.__name__}:{self.label}>"

    @staticmethod
    def _filter_by_label(inst: LabelSingleton, label: str) -> bool:
        # handles "find_instance" value criterion
        return inst.label == label

    def _get_identifiers(self) -> set[Identifier]:
        # If using the "has_identifiers" find mixin
        return { self.label }
