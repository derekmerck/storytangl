"""
Deep and Wide Auditable ChainMap
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional, Union, Literal, ClassVar
from uuid import UUID
import copy



"""
Want an auditable namespace that combines attribs, local state vars, local shape elements

>> entity.foo = 123                      # emits patch, set attrib foo on entity
>> entity.state.bar = 123                # emits patch, set var bar on entity.state
>> entity.shapes.child1.foo = 123        # emits patch, set attrib foo on entity.shapes.child1
>> entity.shapes.0.foo = 123             # emits patch, set attrib foo on entity.shapes.0
>> entity.shapes.1.shapes.add( Node(label="def", foo=456)  # emits patch, add/create el
>> entity.shapes.1.shapes.def.foo        # read attrib foo on entity.shapes.1.shapes.def -> 456

Should be chainable

>> entity0.foo = 100
>> entity1.state.bar = 200
>> entity1.shapes.add( Node(label="cat", foo=300) )

>> with self = ctx( entity0, entity1 ):
>>   self.foo     # read attrib, returns 100
>>   bar          # implicit state keys in ns, returns 200
>>   cat.foo      # implicit shape labels in ns, read attrib foo on entity.shapes.0.foo -> 300

>>   audit_op_log = ctx.op_log()  # list of op patches

audit patch is something simple like (scope_id, crud-op-type, key, value, seq)
then a replay feature and immutable underlying states and shape vecs
"""


OpKind = Literal["create", "read", "update", "delete"]

@dataclass(frozen=True)
class Operation:
    """Immutable op record"""

    path: tuple[str, ...]  # Full key path ('this', 'that', 'foo')
    op: OpKind
    value: Optional[Any] = None
    before: Optional[Any] = None
    seq: int = field(init=False, default_factory=lambda: Operation.incr_op_count)

    op_count: ClassVar[int] = 0
    @classmethod
    def incr_op_count(cls) -> int:
        cls.op_count += 1
        return cls.op_count


@dataclass
class Entity:
    uid: UUID = field(default_factory=UUID, init=False)
    label: Optional[str] = None

    my_var: int = 100


@dataclass
class Scope(Entity):
    state: dict[str, Any] = field(default_factory=dict)
    shapes: dict[str, Entity] = field(default_factory=list)
    behaviors: Any = None

@dataclass
class ScopeProxy:
    scope: Scope

    def __getattr__(self, key: str) -> Any:
        if key in self.scope.state:
            return MapProxy(self.state)[key]
        elif key in self.shapes:
            return ScopeProxy(self.shapes[key])
        raise AttributeError(key)

    def __setattr__(self, name: str, value: Any) -> None:
        ...


# [ scope0, scope1, ..., scopeN ]
class ScopeStack:
    scopes: List[Scope] = field(default_factory=list)

    def items(self) -> ScopeView[KeyPath, Any]:
        ...


class EntityRegistry(dict[UUID, Entity]):
    def add(self, entity: Entity) -> None:
        self[entity.uid] = entity


class Context:
    entity_registry: EntityRegistry = EntityRegistry()
    maps: list[dict | EntityRegistry] = field(default_factory=list)
    audit_log:

# There are 2 directions that we need to take this, through scope distance (chain map) and through nesting maps/entities

@dataclass
class MapProxy(dict):
    data: dict[str, Any]
    path: tuple[str, ...] = field(default_factory=tuple)
    tracker: list[Patch] = field(default_factory=list)

    def __getitem__(self, key):
        obj = self.data[key]
        path = (*self.path, key)
        if isinstance(obj, dict):
            return MapProxy(data=obj, path=path, tracker=self.tracker)
        elif isinstance(obj, Entity):
            return EntityProxy(data=obj, path=path, tracker=self.tracker)
        return obj

    def __setitem__(self, key, value):
        path = (*self.path, key)
        before = self.data.get(key)
        if key in self.data:
            op = "update"
        else:
            op = "create"
        self.data[key] = value
        patch = Patch(
            path=".".join(path),
            op=op,
            value=value,
            before=before
        )
        self.tracker.append(patch)

    def __delitem__(self, key):
        path = (*self.path, key)
        if key not in self.data:
            raise KeyError(key)
        before = self.data.pop(key, None)
        op = "delete"
        patch = Patch(
            path=".".join(path),
            op=op,
            before=before
        )
        self.tracker.append(patch)





class ChangeTracker:
    """Collects patches during a tracked operation"""

    def __init__(self):
        self.patches: List[Patch] = []
        self._tick = 0

    def emit_patch(self, target: str, op: str, before: Any, after: Any):
        """Record a change as a patch"""
        patch = Patch(
            target=target,
            op=op,
            before=before,
            after=after,
            tick=self._tick
        )
        self.patches.append(patch)
        self._tick += 1

    def clear(self):
        """Reset tracker"""
        self.patches = []
        self._tick = 0


class StateProxy:
    """
    Proxy that intercepts property access and tracks changes.
    Preserves the mutable API while generating patches.
    """

    def __init__(self, data: Dict[str, Any], path: str = "", tracker: ChangeTracker = None):
        self._data = data
        self._path = path
        self._tracker = tracker or ChangeTracker()

    def __getattr__(self, key: str) -> Any:
        if key.startswith('_'):
            # Internal attributes bypass proxy
            return object.__getattribute__(self, key)

        value = self._data.get(key)
        current_path = f"{self._path}.{key}" if self._path else key

        # Wrap nested dicts in proxies
        if isinstance(value, dict):
            return StateProxy(value, current_path, self._tracker)
        elif isinstance(value, Entity):
            # Wrap entities in entity proxies
            return EntityProxy(value, current_path, self._tracker)
        else:
            return value

    def __setattr__(self, key: str, value: Any):
        if key.startswith('_'):
            # Internal attributes bypass tracking
            super().__setattr__(key, value)
        else:
            current_path = f"{self._path}.{key}" if self._path else key
            before = self._data.get(key)

            # Emit patch before mutation
            self._tracker.emit_patch(
                target=current_path,
                op="set",
                before=before,
                after=value
            )

            # Now do the actual mutation
            self._data[key] = value


class EntityProxy:
    """Proxy for Entity objects that tracks field changes"""

    def __init__(self, entity: 'Entity', path: str, tracker: ChangeTracker):
        self._entity = entity
        self._path = path
        self._tracker = tracker

    def __getattr__(self, key: str) -> Any:
        if key.startswith('_'):
            return object.__getattribute__(self, key)

        value = getattr(self._entity, key)
        current_path = f"{self._path}.{key}"

        # Wrap nested entities
        if isinstance(value, Entity):
            return EntityProxy(value, current_path, self._tracker)
        elif isinstance(value, dict):
            return StateProxy(value, current_path, self._tracker)
        else:
            return value

    def __setattr__(self, key: str, value: Any):
        if key.startswith('_'):
            super().__setattr__(key, value)
        else:
            current_path = f"{self._path}.{key}"
            before = getattr(self._entity, key, None)

            # Emit patch
            self._tracker.emit_patch(
                target=current_path,
                op="set",
                before=before,
                after=value
            )

            # Mutate the entity
            setattr(self._entity, key, value)


class TrackedContext:
    """
    Context that provides tracked access to state and entities.
    All mutations through this context generate patches.
    """

    def __init__(self, graph: 'Graph', scopes: List['Scope']):
        self.graph = graph
        self.scopes = scopes
        self._tracker = ChangeTracker()

        # Build namespace from scopes
        self._namespace = {}
        for scope in scopes:
            if hasattr(scope, 'state'):
                self._namespace.update(scope.state)

    def __getattr__(self, key: str) -> Any:
        """
        Access state or entities, wrapped in tracking proxies.

        Example:
            ctx.scene  # Returns EntityProxy for scene
            ctx.scene.actor  # Returns EntityProxy for actor
            ctx.scene.actor.name  # Returns actual name value
        """
        if key.startswith('_'):
            return object.__getattribute__(self, key)

        # First check namespace (state values)
        if key in self._namespace:
            value = self._namespace[key]
            if isinstance(value, dict):
                return StateProxy(value, key, self._tracker)
            elif isinstance(value, Entity):
                return EntityProxy(value, key, self._tracker)
            else:
                return value

        # Then check for entities by label
        entity = self._find_entity_by_label(key)
        if entity:
            return EntityProxy(entity, key, self._tracker)

        raise AttributeError(f"No state or entity found for '{key}'")

    def _find_entity_by_label(self, label: str) -> Optional['Entity']:
        """Find entity in graph by label"""
        for scope in self.scopes:
            if hasattr(scope, 'find_elements'):
                for element in scope.find_elements(label=label):
                    return element
        return None

    def get_patches(self) -> List[Patch]:
        """Get all patches recorded since last clear"""
        return list(self._tracker.patches)

    def clear_patches(self):
        """Clear patch history"""
        self._tracker.clear()


# Example usage showing how effects work with tracking

def example_effect(ctx: TrackedContext):
    """
    Effect that uses natural mutation API but generates patches.
    """
    # These mutations are tracked
    ctx.scene.actor.name = "Bob"
    ctx.scene.actor.health = 100
    ctx.player_score = ctx.player_score + 10

    # Can still read naturally
    if ctx.scene.actor.health > 0:
        ctx.scene.status = "active"


def apply_effect_with_tracking(effect_func, graph, scopes) -> List[Patch]:
    """
    Execute an effect function and capture its patches.
    """
    # Create tracked context
    ctx = TrackedContext(graph, scopes)

    # Run effect (mutations are tracked)
    effect_func(ctx)

    # Extract patches
    patches = ctx.get_patches()

    return patches


# Alternative: Effect Descriptor for Class Methods

class tracked_effect:
    """
    Decorator that automatically tracks mutations in effects.
    """

    def __init__(self, method):
        self.method = method

    def __get__(self, obj, objtype=None):
        def wrapper(*args, **kwargs):
            # Find context argument
            ctx = None
            for arg in args:
                if isinstance(arg, (TrackedContext, dict)):
                    ctx = arg
                    break

            if ctx is None:
                # No context, run untracked
                return self.method(obj, *args, **kwargs)

            # Wrap context if needed
            if not isinstance(ctx, TrackedContext):
                ctx = TrackedContext(obj.graph, obj.scopes)

            # Run method with tracking
            result = self.method(obj, ctx, *args, **kwargs)

            # Store patches on the object or return them
            patches = ctx.get_patches()
            if hasattr(obj, '_patches'):
                obj._patches.extend(patches)

            return result

        return wrapper


class MyEntity(Entity):
    """Example entity with tracked effects"""

    @tracked_effect
    def apply_damage(self, ctx, amount: int):
        """This effect automatically generates patches"""
        ctx.actor.health = ctx.actor.health - amount
        if ctx.actor.health <= 0:
            ctx.actor.status = "dead"
            ctx.scene.active_actors = ctx.scene.active_actors - 1


# Integration with Phase System

def update_phase(ir: 'StoryIR', layers: 'LayerStack') -> Tuple['StoryIR', List[Patch]]:
    """
    Update phase that runs effects and collects patches.
    """
    # Create tracked context
    ctx = TrackedContext(ir.graph, layers.to_scopes())

    # Find and run effects for current cursor
    cursor = ir.graph.get_cursor()
    effects = layers.find_behaviors('UPDATE', cursor)

    all_patches = []
    for effect in effects:
        # Clear tracker before each effect
        ctx.clear_patches()

        # Run effect (mutations are tracked)
        effect.func(cursor, ctx)

        # Collect patches
        all_patches.extend(ctx.get_patches())

    # Apply patches to create new IR
    new_ir = apply_patches_to_ir(ir, all_patches)

    return new_ir, all_patches


def apply_patches_to_ir(ir: 'StoryIR', patches: List[Patch]) -> 'StoryIR':
    """
    Apply patches to create new immutable IR.
    This is where we convert from mutable operations to immutable data.
    """
    new_ir = ir

    for patch in patches:
        # Parse target path
        path_parts = patch.target.split('.')

        # Apply patch based on path
        # This would use pyrsistent operations
        if path_parts[0] in ir.state:
            # State update
            new_state = update_nested_pmap(ir.state, path_parts, patch.after)
            new_ir = new_ir.with_state(new_state)
        else:
            # Entity update - need to update shape
            new_shape = update_entity_in_shape(ir.shape, path_parts, patch.after)
            new_ir = new_ir.with_shape(new_shape)

    return new_ir