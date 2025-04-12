import logging

from pydantic import model_validator

from ..singleton import SingletonEntity

logger = logging.getLogger("tangl.singleton.ref")
logger.setLevel(level=logging.DEBUG)

class InheritingSingleton:
    """
     A SingletonEntity mixin that supports attribute inheritance from another instance of the same class.

     This class allows creating new singleton instances by inheriting properties from an existing instance,
     identified by its label. This is useful for creating variations of a base entity without repeating common
     attributes. The inheritance is controlled by the 'from_ref' keyword argument.

     Be careful to load them in order, the code does not provide any dependency resolution.

     Parameters:
         from_ref (UniqueLabel): The label of the reference entity to inherit attributes from.

     Methods:
         __init__: Initializes the entity, optionally inheriting attributes from the reference entity.
     """
    @model_validator(mode='before')
    @classmethod
    def _handle_instance_inheritance(cls: type[SingletonEntity], data):
        # logger.debug( data )
        from_ref = data.pop('from_ref', None)
        if from_ref:
            if from_ref not in cls._instances:
                raise ValueError(f"No such reference instance: {from_ref} for {data['label']}")
            ref = cls.get_instance(from_ref)    # this raises a native key error if from_ref is not a key
            for field_name in cls.model_fields:
                if field_name in [ "uid_", "label_"]:
                    continue
                logger.debug( f"{field_name}: {getattr(ref, field_name)}")
                logger.debug( f"data[{field_name}]: {data.get(field_name)}")
                data.setdefault( field_name, getattr( ref, field_name ))

        return data


