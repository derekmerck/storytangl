from __future__ import annotations
from typing import Union, ClassVar, Self, Any
from uuid import UUID
import hashlib
import logging
from importlib import resources
import functools

from pydantic import BaseModel, ConfigDict
import shortuuid

from tangl.type_hints import Identifier

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class Singleton:
    """
    Singletons are immutable and use an object digest as a uid to ensure uniqueness.
    """

    # When mixed into pydantic, singletons should be frozen
    model_config = ConfigDict(frozen=True)
    digest: bytes = None

    @property
    def uid(self) -> UUID:
        if self.digest:
            return UUID(bytes=self.digest[0:16])

    def short_uid(self) -> str:
        return shortuuid.encode(self.uid)

    @classmethod
    def compute_digest(cls, **kwargs) -> bytes:
        """
        Override this method in subclasses to implement specific hash computation.
        """
        raise NotImplementedError("Subclasses must implement a `compute_digest` method if necessary")

    # Instance Management

    # Base class has to init its own instance table, bc it doesn't call
    # its own __init_subclass__
    _instances: ClassVar[dict[UUID, Singleton]] = dict()

    def __init_subclass__(cls, **kwargs):
        """
        Provide a separate table for each subclass to manage their own instances,
        since digests are only guaranteed unique within a class namespace.

        If you want to refer to a super-classes instance table, just set the
        _instance map in the class definition, so it won't be overwritten.
        """
        if cls.__dict__.get("_instances") is None:
            cls._instances = dict()
        super().__init_subclass__(**kwargs)

    def __new__(cls, *, digest: bytes = None, **kwargs):
        """This allows re-newing a singleton entity by its digest."""
        if not digest:
            try:
                digest = cls.compute_digest(**kwargs)
            except TypeError:
                pass
        logger.debug(f"digest: {digest!r}")
        if digest:
            uid = UUID(bytes=digest[0:16])
            if cls.has_instance(uid):
                logger.debug("found self in _instances, should decline to init")
                return cls.get_instance(uid)
        logger.debug('newing self normally')
        return super().__new__(cls)

    @classmethod
    def pre_init(cls, *, digest: bytes = None, **kwargs) -> dict[str, Any]:
        # create a digest if possible
        if not digest:
            try:
                digest = cls.compute_digest(**kwargs)
                if digest:
                    kwargs['digest'] = digest
            except TypeError:
                pass
        else:
            kwargs['digest'] = digest
        return kwargs

    def __init__(self, **kwargs) -> None:
        try:
            if self.has_instance(self.uid):
                return
        except AttributeError:
            pass
        kwargs = self.pre_init(**kwargs)
        if isinstance(self, BaseModel):
            super().__init__(**kwargs)
        else:
            if x := kwargs.pop('digest', None):
                self.digest = x
            super().__init__()
        self.finalize()

    def finalize(self, recompute_digest: bool = False):
        if self.digest is None or recompute_digest:
            digest = self.compute_digest(**self.__dict__)
            if digest is not None:
                # Override frozen setattr if computing a deferred digest
                object.__setattr__(self, 'digest', digest)
            else:
                raise ValueError(f"Unable to compute a digest for {self}")
        self.register_instance(self)

    @classmethod
    def register_instance(cls, instance: Self):
        if instance.uid in cls._instances:
            logger.error(f"Instance {instance.uid} already registered")
            logger.error(f"New instance: {instance!r}")
            logger.error(f"Conflicting instance: {cls._instances[instance.uid]!r}")
            raise KeyError(f"Duplicate key {instance.uid} in {cls.__name__}")
        cls._instances[instance.uid] = instance
        logger.debug(f"Instance {instance.uid} registered")

    @classmethod
    def unregister_instance(cls, instance: Self):
        if instance.uid in cls._instances:
            del cls._instances[instance.uid]

    @classmethod
    def discard_instance(cls, key: Identifier):
        if cls.has_instance(key):
            cls.unregister_instance(cls.get_instance(key))

    @classmethod
    def clear_instances(cls, clear_subclasses: bool = False):
        cls._instances.clear()

        if clear_subclasses:
            for cls_ in cls.__subclasses__():
                cls_.clear_instances(clear_subclasses=True)

    @classmethod
    def has_instance(cls, key: Identifier, search_subclasses: bool = False) -> bool:
        """Check for an instance without raising a KeyError"""
        if key in cls._instances:
            return True

        if search_subclasses:
            for cls_ in cls.__subclasses__():
                logger.debug(f"Searching for {key} in {cls_}")
                try:
                    return cls_.has_instance(key, search_subclasses=True)
                except KeyError:
                    pass

        return False

    @classmethod
    def get_instance(cls,
                     key: Identifier,
                     search_subclasses: bool = False,
                     create: bool = False) -> Self:
        """
        Retrieves an instance of the singleton entity by its label.

        :param key: The unique label of the entity to retrieve.
        :param search_subclasses: Whether subclasses should be searched for a matching label.
        :return: The instance of the singleton entity associated with the label.
        :raises KeyError: If no instance with the given label exists.
        """
        if key in cls._instances:
            return cls._instances[key]

        if search_subclasses:
            for cls_ in cls.__subclasses__():
                logger.debug(f"Searching for {key} in {cls_}")
                try:
                    return cls_.get_instance(key, search_subclasses=True)
                except KeyError:
                    pass

        raise KeyError(f"No instance with key <{key}> exists.")

    @classmethod
    def find_instances(cls, **criteria: Any) -> list[Self]:
        from tangl.core.handler.filter_handler import FilterHandler
        return FilterHandler.filter_instances(cls._instances.values(), **criteria)

    @classmethod
    def find_instance(cls, **criteria: Any) -> Union[Self, None]:
        res = cls.find_instances(**criteria)
        if res:
            return res[0]

    def _get_identifiers(self) -> set[Identifier]:
        # If using the "has_identifiers" find mixin
        return { self.digest }

    # Class Utils

    @classmethod
    def hash_value(cls, value: str | bytes) -> bytes:
        if isinstance(value, str):
            value = value.encode('utf-8')
        return hashlib.sha256(value).digest()

    # Serialization

    def __reduce__(self) -> tuple:
        """
        Singletons can be pickled by reference since they are immutable with respect to
        their public interface.

        :returns: tuple: The class and label of the entity, used for reconstructing the
           instance when unpickling.
        """
        return self.__class__.get_instance, (self.uid, )

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs):
        """
        Singleton entities can be serialized by reference since they are immutable
        with respect to their public interface.
        """
        return {
            'obj_cls': self.__class__,
            'uid': self.uid
        }

    def __repr__(self):
        return f"<{self.__class__.__name__}:{self.short_uid()}>"

    # Convenience methods for initializing multiple singleton instances from data.

    @classmethod
    def load_instances(cls, data: dict):
        for label, kwargs in data.items():
            cls(label=label, **kwargs)

    @classmethod
    def load_instances_from_yaml(cls, resources_module: str, fn: str):
        import yaml
        with resources.open_text(resources_module, fn) as f:
            data = yaml.safe_load(f)
        cls.load_instances(data)
