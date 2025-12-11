from abc import ABC
from typing import *

import attr


from scratch.protocols import EntityFactory, EntityMap, Uid
from .utils import as_eid, normalize_list_arg
from tangl.utils.new_eid import new_eid


@attr.define( kw_only=True, slots=False )
class Entity(ABC):
    """Framework for *all* managed game entities"""

    #: *entity id*, unique uuid-based, i.e., "ABC123"
    eid: Uid  = attr.ib( factory=new_eid,
                         metadata={"state": True},
                         eq=False )
    #: *unique id*, base template name or game part identifier, i.e., "my_block"
    uid: Uid = attr.ib( default=None,
                        metadata={"state": True} )

    parent: 'Entity' = attr.ib( default=None, repr=as_eid, eq=False )
    @property
    def root(self):
        res = self
        while res.parent:
            res = res.parent
        return res

    @property
    def path(self) -> str:
        """human-friendly name for instance, unique only within the collection,
        i.e., "scene1/my_block" """
        if self.parent:
            res = self.parent.path + "/"
        else:
            res = ""
        if self.uid:
            return res + self.uid
        else:
            return res + self.eid

    #: A map to all peer instances in this collection
    ctx: EntityMap = attr.ib( factory=dict, repr=False, eq=False )

    #######################
    # Core API
    #######################

    locals: Dict = attr.ib( factory=dict )
    # Scratch variables available to this entity

    def ns(self) -> dict:
        """Generate a cascaded namespace for locals and other named vars
        specific to this entity.
        Cascades by parent and by superclass for subclasses that call
        `super().ns(_ns)` in the override
        Stacks namespace elements for evals, execs, and str renders"""
        _ns = {}
        if self.ctx and hasattr( self.ctx, "ns" ):
            _ns |= self.ctx.ns( )
        if self.parent:
            _ns |= self.parent.ns( )  # adds actors and other things
        _ns |= self.locals
        return _ns

    locked: bool = False  # Object is unavailable
    forced: bool = False  # Object has been _forced_ to be available, ctx is dirty

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def force(self):
        """When an entity is forced, its entire lineage must also be marked forced
        so calls to parent.avail() also return ok"""
        el = self
        el.forced = True
        while el.parent is not None:
            el = el.parent
            el.forced = True

    def avail(self, force: bool = False, **kwargs) -> bool:
        """subclass.avail(**) should call super().avail(**)
           Key subclass.avail(**) features:
           - Conditional: entity conditions are satisfied by current state
           - Traversable: reference entity is available
        """
        if self.locals.get("avail") == "ignore":
            return True
        if force:
            self.force()
        if self.parent:
            if not self.parent.avail(force=force, **kwargs) and not self.forced:
                return False
        #     print( f"parent is: {self.parent.avail()}")
        # print( f"root {self.root.uid} is locked: {self.root.locked}")
        return (not self.locked) or self.forced

    #######################
    # BOOKKEEPING
    #######################

    _entity_types: ClassVar[Dict] = dict()
    # class map for entity subtypes
    factory: EntityFactory = attr.ib( default=None, eq=False, repr=False )
    entity_typ: str = None
    # If this is set, object will attempt to cast itself to this type on instantiation
    templates: List[str] = attr.Factory( factory=list )

    @classmethod
    def _lookup_entity_typ(cls, entity_typ: Union[Type['Entity'], str], default: Type['Entity'] = None) -> Type['Entity']:
        if isinstance( entity_typ, str ):
            entity_key = entity_typ
        elif hasattr( entity_typ, "__name__"):
            entity_key = entity_typ
        else:
            raise TypeError(f"Unable to determine entity_typ_key from {entity_typ}")
        try:
            return cls._entity_types[entity_key]
        except KeyError:
            if default:
                return default
            raise

    @classmethod
    def __init_entity_subclass__(cls, entity_typ: Optional[str] = None, **kwargs):
        """Adds a type to the class family using __class__.name or
        explicit kwargs['entity_typ'] as the key."""
        # print( f"Adding subclass { cls.__name__ }" )
        key = entity_typ or cls.__name__
        cls._entity_types[key] = cls

    def __new__(cls, *args, **kwargs):
        """Figure out if the object wants to be structured differently
        than the family-generic type name.

        There are several possibilities here.

        Figure out the _family_

        - assume the family is cls
        - if there is a kwargs['entity_typ_hint'], this is being structured
          as a child; the _family_ is the entity_typ_hint (probably it's the same as cls)
        - if there is a factory override for the family, use that instead
          ie, Scene may have been overridden in kwargs['factory'].class_map

        Figure out the specific subtype

        - Once we know the class family, check to see if there is an explicit
          kwargs[entity_typ], ie, this Block may be a Challenge.  If there is,
          lookup the entity_typ in the family._class_map and use that instead

        - if there is an entity_typ but no such entity_typ in the family._class_map,
          this may be a blind-inflation, so we need to check the base Entity._class_map
        """

        entity_family = cls  # will be the type hint if structured as child

        try:
            factory = kwargs.get("factory")  # type: EntityFactory
            working_entity_typ = factory._lookup_entity_typ(entity_family) # type: Type[Entity]
            # print( f'Using factory cls {working_entity_typ}' )
        except (AttributeError, KeyError) as e:  # no factory or missing key
            # print( e )
            # print( f"No factory or missing key for {entity_family}")
            working_entity_typ = entity_family

        if "entity_typ" in kwargs:
            entity_typ_kwarg = kwargs.get('entity_typ')  # type: Union[Type[Entity], str]
            try:
                working_entity_typ = factory.get_entity_class(entity_typ_kwarg) # type: Type[Entity]
                # print(f'Using factory cls {working_entity_typ}')
            except (AttributeError, KeyError) as e:  # no factory or missing key
                # print(e)
                # print(f"No factory or missing key for {entity_family}")
                pass

            try:
                cls_ = working_entity_typ._entity_types[entity_typ_kwarg]
                # print( f"using registered subtype {cls_} for {entity_typ_kwarg}")
            except KeyError:
                # print( f"no registered subtype for {entity_typ_kwarg}")
                cls_ = working_entity_typ

        else:
            cls_ = working_entity_typ

        return super().__new__(cls_)

    def __init__(self, *args, **kwargs):

        # Consume templates kwarg
        factory = kwargs.get( "factory" )
        if factory:
            important_ = {}
            try:
                templ = factory.get_template( self.__class__, kwargs['uid'] )
                important_ |= { k: v[:-2] for k, v in templ.items()
                                if v and hasattr( v, "endswith") and v.endswith( ".!!" ) }
                # print( f"Found template for {self.__class__}, {kwargs.get('uid')}" )
                # print( templ )
            except KeyError:
                # print( f"No template available for {self.__class__}, {kwargs.get('uid')}" )
                templ = {}
            if "templates" in kwargs:
                # print( f"found templates key")
                templs = kwargs.pop( "templates" )
                templs = normalize_list_arg( templs )
                templ_ = factory.templates.get_templates( self.__class__, *templs )
                important_ |= { k: v[:-2] for k, v in templ_.items()
                                if v and hasattr( v, "endswith") and v.endswith( ".!!" ) }
                templ = templ_ | templ  # this order prefers entries from the uid template
            kwargs = templ | kwargs | important_
            # this order prefers entries from the explicit kwargs but preserves important

        # pre-process kwargs
        kwargs = self._structure_children(**kwargs)
        try:
            self.__attrs_init__( **kwargs )
        except TypeError:
            print( kwargs )
            raise

    def _structure_children(self, **kwargs):
        """Structuring entity children can be complicated!"""

        factory = kwargs.get( 'factory' )  # type: EntityFactory
        ctx = kwargs.get( 'ctx', {} )

        for field in attr.fields(self.__class__):
            # print( field.type.__class__ )
            hint = field.type

            if hasattr(hint, "__mro__") and hint.__mro__[0] in [dict, list]:
                # can't parse the child-type out of 'dict' or 'list' hints
                raise TypeError(f"{self.__class__}.{field.name}: Use 'Dict|List[]' instead of dict|list[] for typing.")

            def create_child(v, uid_):
                # helper func to instantiate new child from str or dict
                if isinstance(v, Entity):
                    # pre-instantiated
                    return v
                if isinstance(v, str):
                    # update v if there is a "consumes_str" flag on a field
                    for field in attr.fields(child_cls):
                        if "consumes_str" in field.metadata:
                            v = {field.name: v}
                            break
                if isinstance(v, dict):
                    if not v.get("uid"):
                        v["uid"] = uid_
                    el = child_cls(**v, parent=self, ctx=ctx, factory=factory)
                    return el
                raise TypeError(f"Couldn't transform kwargs into an entity: {kwargs}")

            child_cls = Entity
            try:
                if hint.__origin__ == dict and issubclass(hint.__args__[1], Entity):
                    # pre-cast the dict of dicts to the proper class
                    child_cls = hint.__args__[1]
                    # print( "child_cls", child_cls )
                    res = {}
                    for k, v in kwargs.get(field.name, {}).items():
                        uid_ = k
                        el = create_child(v, uid_)
                        res[k] = el
                    kwargs[field.name] = res

                elif hint.__origin__ == list and issubclass(hint.__args__[0], Entity):
                    # pre-cast the list of dict to the proper class
                    child_cls = hint.__args__[0]
                    res = []
                    for i, v in enumerate(kwargs.get(field.name, [])):
                        uid_ = f"{field.name[0:2]}{i}"
                        el = create_child(v, uid_)
                        res.append(el)
                    kwargs[field.name] = res

            except (KeyError) as e:
                # Major concern if it happens
                print( "KeyError", field.name, e )
                raise

            except (ValueError, AttributeError) as e:
                if '__origin__' in str(e) or '__args__' in str(e):
                    # Expected failure
                    pass
                else:
                    # Unknown failure
                    print( type(e), field.name, e )
                    print( kwargs.get( 'uid' ), child_cls )
                    raise

        return kwargs

    registered: ClassVar[bool] = True
    # classes can decide if they want to be included in the context
    # for example, Role's are only called indirectly via Scene, so they
    # do not need to be registered

    def __attrs_post_init__(self):
        if self.registered:
            self.ctx[self.eid] = self

    def __init_entity__(self, **kwargs):
        """Called explicitly during ctx instantiation after the base features are stable,
        This initializes DOWN instead of up, as __attrs_post_init__ does"""

        for field in attr.fields(self.__class__):
            hint = field.type
            try:
                if hint.__origin__ == dict:
                    for v in getattr( self, field.name).values():
                        # print( v )
                        v.__init_entity__(**kwargs)
                elif hint.__origin__ == list:
                    for v in getattr( self, field.name):
                        # print( v )
                        v.__init_entity__(**kwargs)
            except (AttributeError, KeyError, TypeError) as e:
                # print( e )
                pass

    #######################
    # SERIALIZATION
    #######################

    def as_dict(self):
        """Abbreviated dict representation that requires a factory to re-create"""
        def _filt( field: attr.Attribute, value ):
            res = "state" in field.metadata and \
                  value != field.default
            return res

        res = attr.asdict(self, recurse=True, filter=_filt)
        return res

    # def __getstate__(self) -> dict:
    #     # noinspection PyDictCreation
    #     state = {**self.__dict__}  # shallow copy, change keys non-destructively
    #     # print( "Getting state" )
    #     from tangl.31.utils.singleton import Singletons
    #     # don't need the pickle to contain the factory or templates
    #     for k, v in state.items():
    #         if isinstance( v, Singletons ):
    #             state[k] = v.uid
    #     return state
    #
    # def __setstate__(self, state):
    #     if state.get( "factory" ) and isinstance( state.get( "factory" ), str ):
    #         from .factory import EntityFactory
    #         state['factory'] = EntityFactory.instance( state['factory'] )
    #     # print( "Setting state" )
    #     self.__dict__.update( state )

    #######################
    # BUILT-INS
    #######################

    __hash__ = object.__hash__  # Entity uses object hash

    def __eq__(self, other):
        """Entity equivalence is by comparing attrs field values"""
        try:
            for field in self.__attrs_attrs__:
                # print( field.name, field.eq )
                if field.eq is False:
                    continue
                this = getattr(self, field.name)
                that = getattr(other, field.name)
                if this != that:
                    raise ValueError
            return True

        except (AttributeError, ValueError):
            return False
