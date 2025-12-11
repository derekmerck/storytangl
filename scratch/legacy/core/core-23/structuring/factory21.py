"""
Factories provide a stash of templates and class type overrides
"""

from collections import UserDict
from typing import *

import attr

from tangl.31.utils.singleton import Singletons
from .protocols import Uid
from .entity import Entity
from .utils import normalize_list_arg


def _normalize_entity_type(entity_typ: Union[Type[Entity]]) -> str:
    if isinstance(entity_typ, str):
        return entity_typ
    elif isinstance(entity_typ, type) and issubclass(entity_typ, Entity):
        return entity_typ.__name__
    raise ValueError( f"{entity_typ} is neither a string nor an Entity")


EntityType = TypeVar('EntityType', bound=Entity)  # Tells users to expect Entity or a subclass of Entity

class EntityTemplates(UserDict):  # uid -> kwargs

    def add_template(self, entity_family: Union[Type[Entity], str], uid: str, **kwargs):
        entity_family = _normalize_entity_type( entity_family )
        # print( f"adding template {kwargs}")
        self.data[(entity_family, uid)] = kwargs

    def get_templates(self, entity_family: Union[Type[Entity], str], *uids: Uid ) -> Dict:
        kwargs = {}
        for uid_ in uids:
            templ_ = self.get_template(entity_family, uid_)
            kwargs |= templ_
            # Note that this is a destructive shallow update
            # use something like "deep_merge" above to support
            # nested field updates
        return kwargs

    def get_template(self, entity_family: Union[Type[Entity], str], uid: Uid) -> Dict:
        entity_family = _normalize_entity_type( entity_family )
        try:
            kwargs = {**self.data[(entity_family, uid)]}
        except KeyError:
            # Ignore missing templates
            return {}
        except TypeError:
            print( self.data.keys() )
            raise

        if "templates" in kwargs:
            templs = kwargs.pop( 'templates' )
            templs = normalize_list_arg( templs )
            kwargs_ = self.get_templates( entity_family, *templs )
            kwargs = kwargs_ | kwargs

        return kwargs

    def __repr__(self):
        return super().__repr__()


from tangl.31.utils.new_eid import new_eid

@attr.define
class EntityFactory(Singletons):

    _instances: ClassVar[dict] = dict()

    uid: str = new_eid
    templates: EntityTemplates = attr.ib( factory=EntityTemplates )

    def add_template(self, entity_family: Union[Type[Entity], str], uid: Uid, **kwargs ):
        return self.templates.add_template( entity_family, uid, **kwargs )

    def get_template(self, entity_family: Union[Type[Entity], str], uid: Uid):
        # check for override, ie, ImprovedHub -> Hub
        if entity_family in self._entity_types.values():
            entity_family = { v: k for k, v in self._entity_types.items() }[entity_family]
        return self.templates.get_template( entity_family, uid )

    def get_templates(self, entity_family: Union[Type[Entity], str], *uids: Uid):
        # check for override, ie, ImprovedHub -> Hub
        if entity_family in self._entity_types.values():
            entity_family = { v: k for k, v in self._entity_types.items() }[entity_family]
        return self.templates.get_templates( entity_family, *uids )

    _entity_types: Dict[str, Type[Entity]] = attr.ib(factory=dict)

    def add_entity_class(self, cls: Type[Entity], entity_typ: str=None):
        if not entity_typ:
            entity_typ = cls.__name__
        self._entity_types[ entity_typ] = cls
    #
    # def get_entity_class(self, entity_typ: Union[Type[Entity], str]) -> Type[Entity]:
    #     key = _normalize_entity_type(entity_typ)
    #     if key in self._entity_types:
    #         return self._entity_types[ key]
    #     # Not registered, but valid
    #     if isinstance( entity_typ, str ) and entity_typ in Entity._entity_types:
    #         return Entity._entity_types.get(entity_typ)
    #     if isinstance( entity_typ, type ) and issubclass( entity_typ, Entity ):
    #         return entity_typ
    #     raise KeyError(f"No entity registered for {entity_typ}")

    # this is the same signature as classmethod Entity._lookup_entity_typ
    def _lookup_entity_typ(self, entity_typ: Union[Type[Entity], str],
                           default: Type['Entity'] = None) -> Type[Entity]:
        if isinstance( entity_typ, str ):
            entity_key = entity_typ
        elif hasattr( entity_typ, "__name__"):
            entity_key = entity_typ.__name__
        else:
            raise TypeError(f"Unable to determine entity_typ_key from {entity_typ}")
        try:
            return self._entity_types[entity_key]
        except KeyError:
            if default:
                return default
            raise

    def new_entity(self, entity_typ: Union[Type[Entity], str], **kwargs) -> EntityType:
        try:
            cls = self._lookup_entity_typ( entity_typ )
            return cls( **kwargs, factory=self )
            # factory=self enables uid and template kwargs, child class remapping
        except KeyError as e:  # problem with class map
            print( f"problem with class map for {entity_typ}")
            raise
        # except TypeError as e:  # problem with args
        #     print( e )
        #     print( cls, uid )
        #     raise

