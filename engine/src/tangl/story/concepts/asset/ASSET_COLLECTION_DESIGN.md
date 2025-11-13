# Asset Collection System Design
## Generic Story-Layer Framework for Managing Asset Collections

**Status:** Draft/Tentative - Pending MVP validation  
**Layer:** Application (tangl.story.concepts.asset)  
**Version:** 3.7

---

## Executive Summary

This document defines a **generic asset collection framework** at the story (application) layer that supports:
- **Wallets** - countable/fungible assets (gold, tokens, currency)
- **Inventories** - unconstrained discrete asset collections (bag of items)
- **Loadouts** - constrained discrete asset collections with slots/validation (outfits, vehicles, credentials)

Domain-specific implementations (wearables, vehicle parts, documents) are **author-layer mechanics** that build on these application-layer primitives.

---

## Architectural Layers

```
┌─────────────────────────────────────────────────────────────┐
│ AUTHOR LAYER (tangl.mechanics)                              │
│                                                             │
│  OutfitManager    VehicleManager    CredentialsPacket       │
│  DeckManager      RobotLoadout      etc.                    │
│                                                             │
│  Domain-specific rules, validation, rendering               │
└─────────────────────────────────────────────────────────────┘
                          ↓ extends
┌─────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER (tangl.story.concepts.asset)              │
│                                                             │
│  AssetCollection (abstract base)                            │
│    ├─ AssetWallet (countable assets)                        │
│    ├─ AssetInventory (discrete, no constraints)             │
│    └─ ComponentManager (discrete, with constraints)         │
│                                                             │
│  Generic patterns, reusable validation, dispatch hooks      │
└─────────────────────────────────────────────────────────────┘
                          ↓ uses
┌─────────────────────────────────────────────────────────────┐
│ CORE LAYER (tangl.core)                                     │
│                                                             │
│  AssetType (singleton definition)                           │
│  DiscreteAsset (wrapped node for graph)                     │
│  CountableAsset (unwrapped type for counting)               │
│                                                             │
│  Foundational primitives, no domain knowledge               │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### Asset Types

**AssetType** (singleton definition)
- Immutable definition shared across all instances
- Loaded from YAML or created programmatically
- Instance inheritance via `from_ref` pattern
- Examples: "iron_sword", "gold_coin", "passport"

**CountableAsset** (fungible)
- Tracked by count/quantity in a wallet
- No graph nodes created
- Examples: currency, tokens, resources

**DiscreteAsset** (unique)
- Wrapped in graph nodes with instance state
- Can be linked, owned, modified individually
- Examples: specific sword, specific document

### Collection Types

#### 1. AssetWallet (Countable Collections)

**Purpose:** Manage counts of fungible assets

**Use Cases:**
- Currency systems (gold, gems, credits)
- Resources (wood, stone, food)
- Tokens/points (experience, reputation)
- Consumables (potions, ammo)

**Characteristics:**
- No graph nodes
- Fast addition/subtraction
- Overflow/underflow checking
- Value aggregation

**Example:**
```python
wallet.gain(gold=50, gems=3)
if wallet.can_afford(gold=30):
    wallet.spend(gold=30)
total_value = wallet.total_value()
```

#### 2. AssetInventory (Unconstrained Discrete Collections)

**Purpose:** Simple bag/container of discrete assets

**Use Cases:**
- General inventory (backpack, chest)
- Quest items collection
- Loot drops
- Storage containers

**Characteristics:**
- Graph nodes for each item
- No slot constraints
- Optional weight/capacity limits
- Simple add/remove

**Example:**
```python
inventory.add(sword_token)
inventory.add(potion_token)
items = inventory.items  # All items
weapons = inventory.items_of_type(Weapon)
```

#### 3. ComponentManager (Constrained Discrete Collections)

**Purpose:** Complex collections with slots, validation, dependencies

**Use Cases:**
- Outfits (clothing layers, body coverage)
- Vehicles (parts, power budgets, slots)
- Credentials (requirements, expiry, dependencies)
- Card decks (zones, limits, costs)
- Robot loadouts (compatibility, resources)

**Characteristics:**
- Graph nodes for each component
- Slot/position constraints
- Resource budgets
- Dependencies between components
- Validation rules
- Aggregate properties

**Example:**
```python
outfit.put_on(jacket)
outfit.open(jacket)  # State transition
errors = outfit.validate_configuration()
desc = outfit.describe()  # "wearing open jacket, jeans"
```

---

## Design: AssetCollection Base

```python
class AssetCollection(ABC):
    """
    Abstract base for all asset collection types.
    
    Provides common interface for:
    - Checking contents
    - Adding/removing assets
    - Validation
    - Serialization
    - Description/rendering
    
    Subclasses implement specific storage and validation logic.
    """
    
    def __init__(self, owner: Node):
        """
        Args:
            owner: The node that owns this collection
        """
        self.owner = owner
    
    # ==================
    # Abstract Interface
    # ==================
    
    @abstractmethod
    def contains(self, asset_identifier: str) -> bool:
        """Check if collection contains asset by label/type."""
        ...
    
    @abstractmethod
    def add(self, asset, *, ctx: Context = None) -> None:
        """Add asset to collection with validation."""
        ...
    
    @abstractmethod
    def remove(self, asset, *, ctx: Context = None) -> None:
        """Remove asset from collection."""
        ...
    
    @abstractmethod
    def clear(self) -> None:
        """Remove all assets."""
        ...
    
    @abstractmethod
    def validate(self, *, context: dict = None) -> list[str]:
        """
        Validate current collection state.
        
        Returns:
            List of error messages (empty if valid)
        """
        ...
    
    @abstractmethod
    def describe(self) -> str:
        """Generate narrative description of collection."""
        ...
    
    # ==================
    # Common Helpers
    # ==================
    
    def is_valid(self, *, context: dict = None) -> bool:
        """Check if collection is valid."""
        return len(self.validate(context=context)) == 0
    
    def get_errors(self, *, context: dict = None) -> list[str]:
        """Get validation errors."""
        return self.validate(context=context)
```

---

## Design: AssetWallet (Countable)

```python
class AssetWallet(Counter[str], AssetCollection):
    """
    Collection for countable/fungible assets.
    
    Stores counts keyed by asset label. Does not create graph nodes.
    
    Example:
        wallet = AssetWallet(player)
        wallet.gain(gold=50, gems=3)
        wallet.spend(gold=10)
        wallet.can_afford(gold=30)  # True
        wallet.total_value()  # 43.0 (if gold=1.0, gems=10.0)
    """
    
    def __init__(self, owner: Node):
        AssetCollection.__init__(self, owner)
        Counter.__init__(self)
    
    # ==================
    # Wallet-Specific API
    # ==================
    
    def gain(self, **amounts: float) -> None:
        """
        Add countable assets.
        
        Args:
            **amounts: Keyword args of asset_label=count
            
        Example:
            wallet.gain(gold=50, gems=3)
        """
        self.update(amounts)
    
    def can_afford(self, **amounts: float) -> bool:
        """
        Check if wallet contains sufficient assets.
        
        Args:
            **amounts: Required amounts by asset label
            
        Returns:
            True if all requirements met
        """
        for label, required in amounts.items():
            if self[label] < required:
                return False
        return True
    
    def spend(self, **amounts: float) -> None:
        """
        Remove assets (raises if insufficient).
        
        Args:
            **amounts: Amounts to remove by asset label
            
        Raises:
            ValueError: If insufficient assets
        """
        if not self.can_afford(**amounts):
            raise ValueError(
                f"Insufficient assets: need {amounts}, have {dict(self)}"
            )
        for label, amount in amounts.items():
            self[label] -= amount
    
    def total_value(self, asset_manager: AssetManager = None) -> float:
        """
        Calculate total value of all assets.
        
        Args:
            asset_manager: Manager to look up asset values
            
        Returns:
            Sum of (count * asset.value) for all assets
        """
        if not asset_manager:
            # Try to get from owner's world
            asset_manager = getattr(self.owner.graph, 'asset_manager', None)
        
        if not asset_manager:
            raise ValueError("No asset_manager available for value calculation")
        
        total = 0.0
        for label, count in self.items():
            asset_type = asset_manager.get_countable_type('currency', label)
            total += asset_type.value * count
        return total
    
    # ==================
    # AssetCollection Interface
    # ==================
    
    def contains(self, asset_label: str) -> bool:
        """Check if wallet has any of this asset."""
        return self[asset_label] > 0
    
    def add(self, asset_label: str, amount: float = 1.0, *, ctx: Context = None):
        """Add amount of asset."""
        self.gain(**{asset_label: amount})
    
    def remove(self, asset_label: str, amount: float = 1.0, *, ctx: Context = None):
        """Remove amount of asset."""
        self.spend(**{asset_label: amount})
    
    def clear(self):
        """Remove all assets."""
        Counter.clear(self)
    
    def validate(self, *, context: dict = None) -> list[str]:
        """Validate wallet state (always valid for basic wallet)."""
        return []
    
    def describe(self) -> str:
        """Describe wallet contents."""
        if not self:
            return "empty wallet"
        
        items = sorted(self.items(), key=lambda x: -x[1])
        parts = [f"{count:.0f} {label}" for label, count in items if count > 0]
        return ", ".join(parts)
```

---

## Design: AssetInventory (Unconstrained Discrete)

```python
class AssetInventory(AssetCollection):
    """
    Collection for discrete assets without constraints.
    
    Simple bag/container that holds discrete asset nodes.
    Optional capacity limits, but no slot/compatibility rules.
    
    Example:
        inventory = AssetInventory(player)
        inventory.add(sword_token)
        inventory.add(potion_token)
        items = inventory.items  # All items
        weapons = inventory.items_of_type(Weapon)
    """
    
    def __init__(self, owner: Node, *, max_items: int = None, max_weight: float = None):
        """
        Args:
            owner: Owning node
            max_items: Maximum number of items (None = unlimited)
            max_weight: Maximum weight capacity (None = unlimited)
        """
        super().__init__(owner)
        self.max_items = max_items
        self.max_weight = max_weight
    
    # ==================
    # Collection Access
    # ==================
    
    @property
    def items(self) -> list[DiscreteAsset]:
        """All items in inventory."""
        return self.owner.find_children(DiscreteAsset)
    
    def items_of_type(self, asset_type: Type[DiscreteAsset]) -> list[DiscreteAsset]:
        """Get items of specific type."""
        return [item for item in self.items if isinstance(item, asset_type)]
    
    def get_item(self, label: str) -> Optional[DiscreteAsset]:
        """Get specific item by label."""
        matches = [item for item in self.items if item.label == label]
        return matches[0] if matches else None
    
    def count(self) -> int:
        """Number of items in inventory."""
        return len(self.items)
    
    def total_weight(self) -> float:
        """Total weight of all items."""
        return sum(
            getattr(item.singleton, 'weight', 0.0) 
            for item in self.items
        )
    
    # ==================
    # Validation
    # ==================
    
    def can_add(self, item: DiscreteAsset) -> tuple[bool, list[str]]:
        """
        Check if item can be added.
        
        Returns:
            (can_add, error_messages)
        """
        errors = []
        
        # Check item count
        if self.max_items is not None:
            if self.count() >= self.max_items:
                errors.append(f"Inventory full ({self.max_items} items)")
        
        # Check weight
        if self.max_weight is not None:
            item_weight = getattr(item.singleton, 'weight', 0.0)
            if self.total_weight() + item_weight > self.max_weight:
                errors.append(
                    f"Too heavy: {self.total_weight() + item_weight:.1f} > {self.max_weight}"
                )
        
        return len(errors) == 0, errors
    
    def validate(self, *, context: dict = None) -> list[str]:
        """Validate current inventory state."""
        errors = []
        
        # Check total count
        if self.max_items is not None:
            if self.count() > self.max_items:
                errors.append(f"Too many items: {self.count()} > {self.max_items}")
        
        # Check total weight
        if self.max_weight is not None:
            total = self.total_weight()
            if total > self.max_weight:
                errors.append(f"Overweight: {total:.1f} > {self.max_weight}")
        
        return errors
    
    # ==================
    # Mutation API
    # ==================
    
    def add(self, item: DiscreteAsset, *, ctx: Context = None) -> None:
        """
        Add item to inventory.
        
        Args:
            item: Discrete asset node
            ctx: Optional context for dispatch
            
        Raises:
            ValueError: If capacity exceeded
        """
        can_add, errors = self.can_add(item)
        if not can_add:
            raise ValueError(f"Cannot add item: {errors}")
        
        # Dispatch validation
        if ctx:
            from tangl.story.dispatch import story_dispatch
            story_dispatch.dispatch(
                item, ctx=ctx, task="validate_inventory_add", inventory=self
            )
        
        # Link item to owner
        self.owner.add_child(item)
        item.owner_id = self.owner.uid
        
        # Lifecycle event
        if ctx:
            story_dispatch.dispatch(
                item, ctx=ctx, task="inventory_add", inventory=self
            )
    
    def remove(self, item: DiscreteAsset, *, ctx: Context = None) -> None:
        """
        Remove item from inventory.
        
        Args:
            item: Item to remove
            ctx: Optional context for dispatch
        """
        if item not in self.items:
            raise ValueError(f"Item {item.label} not in inventory")
        
        # Lifecycle event
        if ctx:
            from tangl.story.dispatch import story_dispatch
            story_dispatch.dispatch(
                item, ctx=ctx, task="inventory_remove", inventory=self
            )
        
        # Unlink from owner
        item.owner_id = None
        self.owner.remove_child(item)
    
    def clear(self):
        """Remove all items."""
        for item in list(self.items):
            self.remove(item)
    
    # ==================
    # AssetCollection Interface
    # ==================
    
    def contains(self, asset_label: str) -> bool:
        """Check if inventory contains item."""
        return self.get_item(asset_label) is not None
    
    def describe(self) -> str:
        """Describe inventory contents."""
        if not self.items:
            return "empty inventory"
        
        count = self.count()
        weight_info = f", {self.total_weight():.1f} lbs" if self.max_weight else ""
        return f"{count} items{weight_info}"
```

---

## Design: ComponentManager (Constrained Discrete)

```python
class ComponentManager(AssetCollection, Generic[CT]):
    """
    Collection for discrete assets with complex constraints.
    
    Supports:
    - Slot/position assignments
    - Layering/priority
    - Resource budgets (power, weight, etc.)
    - Inter-component dependencies
    - State machines
    - Temporal validation (expiry, cooldowns)
    - Context-aware rules (destination, mission)
    - Aggregate property calculation
    
    This is the base class for domain-specific managers like
    OutfitManager, VehicleManager, CredentialsPacket, etc.
    
    Example:
        class OutfitManager(ComponentManager[Wearable]):
            slot_capacity = {BodyRegion.UPPER: 10, ...}
            tracked_resources = []
            
            def is_visible(self, item):
                # Custom visibility logic
                ...
    """
    
    def __init__(self, owner: Node):
        super().__init__(owner)
    
    # ==================
    # Configuration (Override in Subclass)
    # ==================
    
    slot_capacity: ClassVar[dict[str, int]] = {}
    """Maximum components per slot. Empty = no slot constraints."""
    
    tracked_resources: ClassVar[list[str]] = []
    """Resource names to validate (power, weight, etc.)."""
    
    required_components: ClassVar[list[str]] = []
    """Component labels that must be present."""
    
    # ==================
    # Collection Access
    # ==================
    
    @property
    def components(self) -> list[CT]:
        """All components managed by this collection."""
        return self.owner.find_children(DiscreteAsset)
    
    def get_component(self, label: str) -> Optional[CT]:
        """Get component by label."""
        matches = [c for c in self.components if c.label == label]
        return matches[0] if matches else None
    
    def get_component_of_type(self, component_type: Type[CT]) -> Optional[CT]:
        """Get single component of specific type (chassis, engine, etc)."""
        results = [c for c in self.components if isinstance(c, component_type)]
        return results[0] if results else None
    
    def get_components_of_type(self, component_type: Type[CT]) -> list[CT]:
        """Get all components of specific type (weapons, gadgets, etc)."""
        return [c for c in self.components if isinstance(c, component_type)]
    
    def by_slot(self, slot: str) -> list[CT]:
        """Get components in a specific slot."""
        return [
            c for c in self.components 
            if getattr(c.singleton, 'slot', None) == slot
        ]
    
    def by_layer(self, layer: int) -> list[CT]:
        """Get components at a specific layer/priority."""
        return [
            c for c in self.components 
            if getattr(c.singleton, 'layer', 0) == layer
        ]
    
    # ==================
    # Visibility (Override for Complex Rules)
    # ==================
    
    def is_visible(self, component: CT) -> bool:
        """
        Check if component is visible/active.
        
        Override in subclass for domain-specific visibility rules
        (e.g., layering, coverage, occlusion).
        
        Default: Visible if not in 'off' or 'disabled' state.
        """
        state = getattr(component, 'state', None)
        return state not in {'off', 'disabled', 'removed'}
    
    def visible_components(self) -> list[CT]:
        """Get all visible components."""
        return [c for c in self.components if self.is_visible(c)]
    
    # ==================
    # Validation
    # ==================
    
    def validate(self, *, context: dict = None) -> list[str]:
        """
        Full validation. Returns list of error messages.
        
        Runs all validation checks:
        - Required components
        - Resource budgets
        - Inter-component dependencies
        - Temporal constraints
        - Slot capacity
        - Context-specific rules
        - Custom subclass rules
        """
        errors = []
        
        # Required components
        errors.extend(self._check_required_components())
        
        # Resource budgets
        errors.extend(self._validate_resources())
        
        # Dependencies between components
        errors.extend(self._check_dependencies())
        
        # Temporal constraints
        if context and 'current_time' in context:
            errors.extend(self._check_temporal_validity(
                current_time=context['current_time']
            ))
        
        # Slot capacity
        errors.extend(self._check_slot_capacity())
        
        # Context-specific rules
        if context:
            errors.extend(self._validate_in_context(context=context))
        
        # Subclass-specific rules
        errors.extend(self._validate_custom())
        
        return errors
    
    def _check_required_components(self) -> list[str]:
        """Check that required components are present."""
        errors = []
        for required_label in self.required_components:
            if not self.get_component(required_label):
                errors.append(f"Missing required component: {required_label}")
        return errors
    
    def _validate_resources(self) -> list[str]:
        """Check resource budgets (power, weight, etc)."""
        errors = []
        for resource in self.tracked_resources:
            used, capacity = self._check_resource_budget(resource)
            if capacity is not None and used > capacity:
                errors.append(
                    f"{resource} overload: {used:.1f} > {capacity:.1f}"
                )
        return errors
    
    def _check_resource_budget(self, resource: str) -> tuple[float, Optional[float]]:
        """
        Calculate resource usage.
        
        Returns:
            (used, capacity) tuple. capacity=None means unlimited.
        """
        # Get capacity from owner
        capacity = getattr(self.owner, f'max_{resource}', None)
        
        # Sum costs from components
        used = sum(
            getattr(c.singleton, f'{resource}_cost', 0.0)
            for c in self.components
        )
        
        return used, capacity
    
    def _check_dependencies(self) -> list[str]:
        """Validate inter-component dependencies."""
        errors = []
        for component in self.components:
            requires = getattr(component.singleton, 'requires', [])
            for req in requires:
                if not self.get_component(req):
                    errors.append(
                        f"{component.label} requires {req}"
                    )
        return errors
    
    def _check_temporal_validity(self, *, current_time: int) -> list[str]:
        """Check time-based validity (expiry, cooldowns)."""
        errors = []
        for component in self.components:
            # Check expiry
            expiry = getattr(component, 'expiry_time', None)
            if expiry is not None and expiry < current_time:
                errors.append(f"{component.label} expired")
            
            # Check cooldown
            cooldown = getattr(component, 'cooldown_until', None)
            if cooldown is not None and cooldown > current_time:
                errors.append(f"{component.label} on cooldown")
        
        return errors
    
    def _check_slot_capacity(self) -> list[str]:
        """Check slot capacity constraints."""
        errors = []
        for slot, max_count in self.slot_capacity.items():
            actual = len(self.by_slot(slot))
            if actual > max_count:
                errors.append(
                    f"Slot '{slot}' has {actual} components (max {max_count})"
                )
        return errors
    
    def _validate_in_context(self, *, context: dict) -> list[str]:
        """
        Context-specific validation (destination, mission, etc).
        
        Override in subclass for domain-specific context rules.
        """
        return []
    
    def _validate_custom(self) -> list[str]:
        """
        Subclass-specific validation rules.
        
        Override in subclass for additional domain logic.
        """
        return []
    
    # ==================
    # Aggregate Properties
    # ==================
    
    def aggregate_property(self, prop: str, default: float = 0) -> float:
        """
        Sum a property across all components.
        
        Includes:
        - Base value from singleton definition
        - Bonuses from instance state
        - Penalties from instance state
        
        Example:
            total_defense = manager.aggregate_property('defense_bonus')
        """
        total = default
        for component in self.components:
            # From singleton definition
            total += getattr(component.singleton, prop, 0)
            # From instance bonuses
            total += getattr(component, f'{prop}_bonus', 0)
            # From instance penalties
            total -= getattr(component, f'{prop}_penalty', 0)
        return total
    
    # ==================
    # Mutation API
    # ==================
    
    def can_add(self, component: CT) -> tuple[bool, list[str]]:
        """
        Check if component can be added.
        
        Returns:
            (can_add, error_messages)
        """
        # Would need to temporarily add and validate
        # For now, just return True
        # Subclasses can override for pre-checks
        return True, []
    
    def add(self, component: CT, *, ctx: Context = None) -> None:
        """
        Add component with validation.
        
        Args:
            component: Component to add
            ctx: Optional context for dispatch
            
        Raises:
            ValueError: If validation fails
        """
        can_add, errors = self.can_add(component)
        if not can_add:
            raise ValueError(f"Cannot add component: {errors}")
        
        # Dispatch validation
        if ctx:
            from tangl.story.dispatch import story_dispatch
            story_dispatch.dispatch(
                component, ctx=ctx, task="validate_component_add", manager=self
            )
        
        # Link to owner
        self.owner.add_child(component)
        component.owner_id = self.owner.uid
        
        # Lifecycle event
        if ctx:
            story_dispatch.dispatch(
                component, ctx=ctx, task="component_add", manager=self
            )
    
    def remove(self, component: CT, *, ctx: Context = None) -> None:
        """Remove component from manager."""
        if component not in self.components:
            raise ValueError(f"{component.label} not in collection")
        
        # Lifecycle event
        if ctx:
            from tangl.story.dispatch import story_dispatch
            story_dispatch.dispatch(
                component, ctx=ctx, task="component_remove", manager=self
            )
        
        # Unlink
        component.owner_id = None
        self.owner.remove_child(component)
    
    def clear(self):
        """Remove all components."""
        for component in list(self.components):
            self.remove(component)
    
    # ==================
    # AssetCollection Interface
    # ==================
    
    def contains(self, asset_label: str) -> bool:
        """Check if collection contains component."""
        return self.get_component(asset_label) is not None
    
    def describe(self) -> str:
        """
        Generate narrative description.
        
        Override in subclass for rich domain-specific descriptions.
        Default: Simple count.
        """
        visible = self.visible_components()
        if not visible:
            return "no components"
        return f"{len(visible)} components"
```

---

## Mixin Pattern for Owners

```python
class HasAssetWallet:
    """Mixin for nodes with countable asset wallets."""
    
    _wallet: Optional[AssetWallet] = None
    
    @property
    def wallet(self) -> AssetWallet:
        """Access the asset wallet."""
        if self._wallet is None:
            self._wallet = AssetWallet(self)
        return self._wallet


class HasAssetInventory:
    """Mixin for nodes with unconstrained inventories."""
    
    _inventory: Optional[AssetInventory] = None
    
    @property
    def inventory(self) -> AssetInventory:
        """Access the inventory."""
        if self._inventory is None:
            self._inventory = AssetInventory(self)
        return self._inventory


class HasComponents:
    """Mixin for nodes with component managers."""
    
    # Subclass must override
    _component_manager_class: ClassVar[Type[ComponentManager]] = ComponentManager
    
    @property
    def components(self) -> ComponentManager:
        """Access the component manager."""
        return self._component_manager_class(self)
```

---

## Usage Examples

### Example 1: Wallet (Countable Assets)

```python
from tangl.story.concepts.asset import CountableAsset, AssetWallet, HasAssetWallet

# Define currency types
class Currency(CountableAsset):
    value: float = 1.0
    symbol: str = "$"

Currency(label='gold', value=1.0, symbol='🪙')
Currency(label='gems', value=10.0, symbol='💎')

# Use wallet
class Player(Actor, HasAssetWallet):
    pass

player = Player(label='alice', graph=story_graph)

# Transactions
player.wallet.gain(gold=50, gems=3)
print(player.wallet.describe())  # "50 gold, 3 gems"

if player.wallet.can_afford(gold=30):
    player.wallet.spend(gold=30)
    print("Bought sword!")

total = player.wallet.total_value()  # 20 + 30 = 50
```

### Example 2: Inventory (Unconstrained Discrete)

```python
from tangl.story.concepts.asset import AssetType, DiscreteAsset, AssetInventory

# Define item types
class Item(AssetType):
    weight: float = 1.0
    value: int = 10

Item(label='sword', weight=3.5, value=50)
Item(label='potion', weight=0.5, value=20)

# Create tokens
graph = Graph(label='game')
sword = DiscreteAsset[Item](label='sword', graph=graph)
potion = DiscreteAsset[Item](label='potion', graph=graph)

# Use inventory
player = Player(label='bob', graph=graph)
player.inventory.add(sword)
player.inventory.add(potion)

print(player.inventory.describe())  # "2 items, 4.0 lbs"

# Check capacity
if player.inventory.count() < player.inventory.max_items:
    player.inventory.add(another_item)
```

### Example 3: Components (Constrained Discrete)

```python
# See OutfitManager, VehicleManager examples in previous docs
# These are author-layer implementations in tangl.mechanics
```

---

## Migration Path

### Phase 1: MVP - Core Infrastructure
**Goal:** Get basic discrete and countable assets working

**Tasks:**
1. Fix `DiscreteAsset` generic typing
2. Implement `AssetWallet` (countable)
3. Implement `AssetInventory` (simple discrete)
4. Complete `AssetManager` with YAML loading
5. Comprehensive tests for all three

**Deliverables:**
- `test_countable_asset.py` (8 tests)
- `test_discrete_asset.py` (10 tests)
- `test_asset_wallet.py` (12 tests)
- `test_asset_inventory.py` (15 tests)
- `test_asset_manager.py` (12 tests)
- Example YAML files

**Time:** ~1 week

### Phase 2: Application Layer - Component Manager Base
**Goal:** Extract and generalize the pattern

**Tasks:**
1. Create `ComponentManager` base class
2. Port `OutfitManager` to use base
3. Add dispatch hooks for lifecycle events
4. Documentation and examples

**Deliverables:**
- `test_component_manager.py` (20 tests)
- `test_outfit_manager.py` (25 tests)
- API documentation
- Extension guide

**Time:** ~1 week

### Phase 3: Author Layer - Domain Implementations
**Goal:** Prove generalization with multiple domains

**Tasks:**
1. Implement `VehicleManager` in tangl.mechanics
2. Implement `CredentialsPacket` in tangl.mechanics
3. Each with full tests and examples

**Deliverables:**
- Working vehicle builder
- Working credentials validator
- Example stories using both

**Time:** ~2 weeks (1 week per domain)

---

## Open Design Questions

### 1. Naming

**Current:**
- `AssetWallet` - countable
- `AssetInventory` - discrete, unconstrained
- `ComponentManager` - discrete, constrained

**Alternatives:**
- `AssetBag` instead of `AssetInventory`?
- `AssetLoadout` instead of `ComponentManager`?
- `SlottedCollection` instead of `ComponentManager`?

**Decision:** Defer to Derek's preference

### 2. Single vs Multiple Managers

**Option A:** One node can have multiple collection types
```python
class Player(Actor, HasAssetWallet, HasAssetInventory, HasComponents):
    @property
    def outfit(self) -> OutfitManager:
        return OutfitManager(self)
```

**Option B:** Collections are exclusive
```python
class Player(Actor, HasAssetWallet):
    # Can only have wallet, not inventory
```

**Recommendation:** Option A - allow mixing

### 3. Dispatch Integration

**When to emit events?**
- On add/remove? (Yes)
- On state transitions? (Yes)
- On validation? (Maybe - for vetoing)

**How to pass context?**
- Always require `ctx` parameter?
- Make optional with `ctx=None`?

**Recommendation:** Optional context, emit on mutations

### 4. Serialization

**How to serialize collections?**
- Wallet: Just counts dict `{"gold": 50}`
- Inventory: Reference item UIDs `["uid1", "uid2"]`
- ComponentManager: Same as inventory?

**What about state?**
- Wallet: No special state
- Inventory: Capacity limits persisted?
- ComponentManager: Slot assignments persisted on items?

**Recommendation:** Collections serialize as item references, state on items

---

## Success Criteria

### MVP (Phase 1)
✅ `AssetWallet` works with countable assets  
✅ `AssetInventory` works with discrete assets  
✅ Both integrate with `AssetManager`  
✅ YAML loading for asset definitions  
✅ All tests pass  
✅ Can create player with wallet and inventory  

### Application Layer (Phase 2)
✅ `ComponentManager` base class defined  
✅ Supports multiple component types  
✅ Resource budgets, dependencies, validation  
✅ Dispatch hooks for lifecycle events  
✅ `OutfitManager` uses base  

### Author Layer (Phase 3)
✅ At least 2 additional domains implemented  
✅ Each domain has full tests  
✅ Example stories demonstrating usage  
✅ Documentation for creating new managers  

---

## Conclusion

This design provides:
1. **Clear layering** - Core → Application → Author
2. **Incremental implementation** - MVP first, then generalize
3. **Flexibility** - Simple wallets to complex loadouts
4. **Extensibility** - Easy to add new domains

The key insight: **asset collections are a spectrum**, from simple counts to complex constrained systems. The design supports all cases with a common base abstraction while allowing domain-specific specialization.

Next steps: Validate core infrastructure (Phase 1 MVP), then extract patterns (Phase 2), then prove generalization (Phase 3).
