from typing import Type, TYPE_CHECKING, ClassVar
import inspect
import logging

from pydantic._internal._model_construction import ModelMetaclass

logger = logging.getLogger("tangl.entity.casting")

if TYPE_CHECKING:
    from .entity import Entity

class SelfCastingHandler:
    """
    A handler class to facilitate self-casting of entities based on the 'obj_cls' parameter.
    This class provides a mechanism to dynamically cast an instance of a class to a specified
    subclass during its creation.

    Methods:
        normalize_obj_cls(cls, obj_cls): Normalizes and validates the 'obj_cls' parameter to ensure it
                                         is a valid subclass for casting. If 'obj_cls' is a string, it
                                         attempts to resolve it to a subclass of 'cls'.
    """

    @staticmethod
    def normalize_obj_cls(base_cls: Type['Entity'], obj_cls: str | Type['Entity'], _pm = None, **kwargs) -> Type['Entity']:
        """
        Validates and normalizes the 'obj_cls' parameter to ensure it is a valid subclass of 'cls'.
        If 'obj_cls' is a string, the method tries to resolve it to a subclass using the
        'get_subclass_by_name' method.

        Args:
            cls (Type['Entity']): The base class from which the subclass should be derived.
            obj_cls (str | Type['Entity']): The subclass or its string representation to be normalized.

        Returns:
            Type['Entity']: The normalized subclass.

        Raises:
            ValueError: If 'obj_cls' cannot be resolved to a valid subclass of 'cls'.
        """
        if not obj_cls:
            return base_cls

        if isinstance(obj_cls, str):
            obj_cls = base_cls.get_subclass_by_name(obj_cls)

        if not inspect.isclass(obj_cls) or not issubclass(obj_cls, base_cls):
            logger.error(str(base_cls.get_all_subclasses()))
            raise ValueError(f"Unable to determine entity-type for {obj_cls} given base_cls {base_cls}")

        return obj_cls


class SelfCastingMetaclass(ModelMetaclass):
    """
    A custom metaclass that extends Pydantic's ModelMetaclass to inject self-casting behavior
    into entities. This metaclass wraps the '__new__' method of the class being created to
    allow dynamic casting based on the 'obj_cls' parameter provided during instantiation.

    The self-casting logic is implemented in the 'SelfCastingHandler' and is applied to all
    classes using this metaclass, ensuring that instances are always of the correct type
    as specified by 'obj_cls'.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        """
        Creates a new class with self-casting behavior injected. The method wraps the '__new__' method
        of the class being created with logic that casts the instance to a specific subclass if
        'obj_cls' is provided.

        Args:
            mcs: The metaclass instance.
            name (str): The name of the class being created.
            bases (tuple): The base classes of the class being created.
            namespace (dict): The namespace containing the class's attributes and methods.
            **kwargs: Additional keyword arguments passed to the metaclass.

        Returns:
            A new class with self-casting behavior.
        """

        def find_super_new():
            # I'm not sure why this works for mixin superclasses, like those that
            # use "Singleton" as a base themselves, but it appears to work ok.
            for base_cls in bases:
                if '__new__' in base_cls.__dict__:
                    logger.debug(f"Delegating new to {base_cls}")
                    return base_cls.__new__

        # get either the new from the current namespace, or the super() new from the given bases
        original_new = namespace.get('__new__', find_super_new())

        def new_wrapper(cls, *args, obj_cls=None, _pm=None, **new_kwargs):
            handler = getattr(cls, 'self_casting_handler', SelfCastingHandler)
            _cls = handler.normalize_obj_cls(cls, obj_cls, _pm=_pm, **new_kwargs)

            if _cls is not cls:
                logger.debug(f"switching classes from {cls} to {_cls}")
                # we can ignore our original new, bc we are jumping classes entirely
                return _cls.__new__(_cls, *args, **new_kwargs)

            elif original_new:
                try:
                    logger.debug(f"calling original new for {cls} {original_new}")
                    return original_new(cls, *args, **new_kwargs)
                except TypeError:
                    # Tried to call on object
                    pass

            logger.debug(f"finally calling object new for {cls}")
            return object.__new__(cls)

        namespace['__new__'] = new_wrapper

        return super().__new__(mcs, name, bases, namespace, **kwargs)
