# Singleton Asset: Type/Token Pattern

## The Pattern

**Singleton = Immutable Type Definition (Platonic Ideal)**
- Shared across all instances
- Centrally defined, globally consistent
- Changes propagate to all tokens

**Token = Mutable Token (Individual Instance)**
- Wraps the singleton type
- Adds instance-specific state
- Delegates type queries to singleton

```python
# TYPE (Singleton)
class WearableAsset(Singleton):
    """The concept of 'iron_sword' - shared definition."""
    desc: str                   # Type property
    value: int = 1              # Type property
    material: str = "iron"      # Type property
    
    # Instance properties marked with json_schema_extra
    times_worn: int = Field(
        0, 
        json_schema_extra={"is_instance_var": True}
    )

# TOKEN (Graph Node wrapping Singleton)
Wearable = Token[WearableAsset]

# Usage
iron_sword_type = WearableAsset.get_instance('iron_sword')
# → Singleton, exists once globally

my_sword = Wearable('iron_sword', graph=my_graph)
# → Graph node wrapping the singleton
# → Has its own times_worn counter
# → Delegates desc, value, material to singleton
```

---

## Why This is Genius

### Problem 1: Consistency
Without this pattern:
```python
# Create 100 swords in different inventories
for i in range(100):
    sword = Item(name="Iron Sword", damage=10, material="iron")

# Oh no, swords should be silver now
# → Have to find and update 100 instances 😱
```

With this pattern:
```python
# Define type once
iron_sword = WearableAsset(label='iron_sword', material='iron', damage=10)

# Create 100 tokens
for i in range(100):
    sword = Wearable('iron_sword', graph=graph)
    # All delegate to same type

# Update type definition
iron_sword.material = 'silver'  # Can't actually do this (immutable)
# BUT: reload the singleton from updated config
WearableAsset.load_instances('updated_weapons.yaml')
# → All 100 tokens now reference updated type
```

### Problem 2: Memory
Without this pattern:
```python
# 100 swords × 200 bytes each = 20KB
for i in range(100):
    sword = Item(
        name="Iron Sword",
        desc="A well-crafted iron blade with leather grip...",
        damage=10,
        durability=100,
        # ... lots of shared data
    )
```

With this pattern:
```python
# 1 singleton × 200 bytes + 100 nodes × 24 bytes = ~2.6KB
iron_sword_type = WearableAsset(...)  # 200 bytes, once

for i in range(100):
    sword = Wearable('iron_sword')   # 24 bytes (just wraps UUID + state)
```

---

## The Architecture

### Layer 1: Singleton Registry (Type System)

```python
# Defined in world config or loaded from YAML
class WearableAsset(Singleton):
    # TYPE ATTRIBUTES (shared, immutable)
    desc: str
    value: int
    weight: float
    icon: str
    
    # INSTANCE ATTRIBUTES (per-token, mutable)
    times_worn: int = Field(0, json_schema_extra={"is_instance_var": True})
    condition: float = Field(1.0, json_schema_extra={"is_instance_var": True})
    
    # TYPE METHODS (operate on instance vars)
    def put_on(self):
        """Called on token, modifies token state."""
        self.parent.tags.add(f'wearing:{self.label}')
        self.times_worn += 1
    
    def repair(self):
        """Called on token, modifies token state."""
        self.condition = 1.0

# Load from YAML
WearableAsset.load_instances('wearables.yaml')
"""
iron_sword:
  desc: "A sturdy iron blade"
  value: 50
  weight: 3.5
  icon: "⚔️"

leather_boots:
  desc: "Comfortable leather boots"
  value: 20
  weight: 1.0
  icon: "👢"
"""

# Now they exist globally
WearableAsset.get_instance('iron_sword').desc
# → "A sturdy iron blade"
```

### Layer 2: Token Wrapper (Token System)

```python
class Token(Node, Generic[T]):
    """
    Graph node that wraps a Singleton instance.
    
    Delegation pattern:
    - Type attributes → delegated to singleton
    - Instance attributes → stored locally
    - Methods → executed in context of this node
    """
    
    singleton_label: UniqueLabel  # Reference to singleton
    instance_vars: dict[str, Any] # Local state
    
    def __init__(self, singleton_label: str, graph: Graph, **kwargs):
        super().__init__(graph=graph, **kwargs)
        self.singleton_label = singleton_label
        self.instance_vars = {}
        
        # Initialize instance vars from singleton defaults
        singleton_cls = self._get_singleton_class()
        singleton = singleton_cls.get_instance(singleton_label)
        
        for field_name, field in singleton.model_fields.items():
            if field.json_schema_extra and \
               field.json_schema_extra.get('is_instance_var'):
                # Copy default to instance
                self.instance_vars[field_name] = getattr(singleton, field_name)
    
    @property
    def singleton(self) -> T:
        """Get the wrapped singleton instance."""
        singleton_cls = self._get_singleton_class()
        return singleton_cls.get_instance(self.singleton_label)
    
    def __getattr__(self, name: str) -> Any:
        """
        Delegation:
        1. Check instance vars first (mutable state)
        2. Delegate to singleton (type attributes)
        """
        if name in self.instance_vars:
            return self.instance_vars[name]
        
        return getattr(self.singleton, name)
    
    def __setattr__(self, name: str, value: Any):
        """Route writes to instance vars or parent."""
        if name in ['singleton_label', 'instance_vars', 'graph', 'uid', 'label']:
            super().__setattr__(name, value)
        elif hasattr(self, 'instance_vars') and name in self.instance_vars:
            self.instance_vars[name] = value
        else:
            super().__setattr__(name, value)

# Type alias for clarity
Wearable = Token[WearableAsset]
```

### Layer 3: Usage in Story

```python
# In story script or programmatically
my_sword = Wearable('iron_sword', graph=story_graph)

# Type queries (delegated to singleton)
my_sword.desc       # → "A sturdy iron blade" (from singleton)
my_sword.value      # → 50 (from singleton)
my_sword.icon       # → "⚔️" (from singleton)

# Instance state (local to this token)
my_sword.times_worn # → 0 (from instance_vars)
my_sword.condition  # → 1.0 (from instance_vars)

# Modify instance
my_sword.put_on()
my_sword.times_worn # → 1 (instance_vars updated)

# Type unchanged
WearableAsset.get_instance('iron_sword').times_worn
# → Still 0 (singleton default)

# Create another token
your_sword = Wearable('iron_sword', graph=story_graph)
your_sword.times_worn  # → 0 (fresh instance)
my_sword.times_worn    # → 1 (independent instance)
```

---

## Asset Manager Role

```python
class AssetManager:
    """
    Manages singleton asset types for a world.
    
    Responsibilities:
    1. Load asset type definitions from config
    2. Register singleton classes
    3. Provide factory methods for creating tokens
    """
    
    def __init__(self):
        self.asset_classes: dict[str, Type[Singleton]] = {}
    
    def register_asset_class(self, name: str, cls: Type[Singleton]):
        """Register a singleton asset type class."""
        self.asset_classes[name] = cls
    
    def load_assets_from_file(self, asset_type: str, filepath: Path):
        """
        Load asset instances from YAML.
        
        Example:
        asset_manager.load_assets_from_file('wearables', 'wearables.yaml')
        """
        cls = self.asset_classes.get(asset_type)
        if not cls:
            raise ValueError(f"Unknown asset type: {asset_type}")
        
        cls.load_instances(filepath)
    
    def create_token(
        self,
        asset_type: str,
        singleton_label: str,
        graph: Graph
    ) -> Token:
        """
        Create a graph node token for an asset.
        
        Example:
        token = asset_manager.create_token('wearables', 'iron_sword', graph)
        """
        cls = self.asset_classes[asset_type]
        wrapper_cls = Token[cls]
        return wrapper_cls(singleton_label, graph=graph)
    
    def get_asset_type(self, asset_type: str, label: str) -> Singleton:
        """Get the singleton type definition."""
        cls = self.asset_classes[asset_type]
        return cls.get_instance(label)


# World setup
asset_manager = AssetManager()
asset_manager.register_asset_class('wearables', WearableAsset)
asset_manager.load_assets_from_file('wearables', 'wearables.yaml')

# Now available globally
asset_manager.get_asset_type('wearables', 'iron_sword').desc
# → "A sturdy iron blade"
```

---

## Resource Manager (Files/Media)

Separate concern: managing on-disk assets.

```python
class ResourceManager:
    """
    Manages file-based resources (images, audio, etc).
    
    NOT about game assets - this is about media files.
    """
    
    def __init__(self, resource_path: Path):
        self.resource_path = resource_path
        self.icon_cache: dict[str, str] = {}
        self.image_cache: dict[str, bytes] = {}
    
    def get_icon_url(self, icon_name: str) -> str:
        """Get URL for an icon."""
        return f"/assets/icons/{icon_name}.png"
    
    def get_image_data(self, image_name: str) -> bytes:
        """Load image file."""
        if image_name not in self.image_cache:
            path = self.resource_path / 'images' / f'{image_name}.png'
            self.image_cache[image_name] = path.read_bytes()
        return self.image_cache[image_name]
    
    def get_audio_url(self, audio_name: str) -> str:
        """Get URL for audio file."""
        return f"/assets/audio/{audio_name}.mp3"


# World setup includes both
world = World(
    label='my_world',
    script_manager=script_manager,
    asset_manager=asset_manager,      # Singleton game assets
    resource_manager=resource_manager  # File-based media
)
```

---

## Script Format for Assets

### YAML Definition

```yaml
# wearables.yaml (loaded by AssetManager)
iron_sword:
  desc: "A sturdy iron blade"
  value: 50
  weight: 3.5
  icon: "sword_iron"
  damage: 15
  durability: 100

leather_boots:
  desc: "Comfortable leather boots"
  value: 20
  weight: 1.0
  icon: "boots_leather"
  armor: 2

health_potion:
  desc: "Restores 50 health"
  value: 15
  weight: 0.2
  icon: "potion_red"
  healing: 50
```

### Story Script Reference

```yaml
# story.yaml
label: my_story
metadata:
  title: "Adventure"
  author: "Me"

# Load asset types (tells world to load wearables.yaml)
assets:
  - asset_type: wearables
    source: wearables.yaml

scenes:
  treasure_room:
    blocks:
      entrance:
        content: "You find a chest!"
        
        # Create token in player inventory
        effects:
          - "player.acquire_asset('wearables', 'iron_sword')"
        
        actions:
          - text: "Continue"
            successor: hallway
```

### Programmatic Token Creation

```python
# In block effect handler
def acquire_asset(player: Actor, asset_type: str, asset_label: str):
    """Give player a token of an asset."""
    
    # Create token
    token = player.graph.world.asset_manager.create_token(
        asset_type,
        asset_label,
        graph=player.graph
    )
    
    # Add to player's wallet/inventory
    player.inventory.add(token)
```

---

## Benefits Recap

### 1. Consistency
```python
# Update type definition
WearableAsset.load_instances('updated_wearables.yaml')
# → All existing tokens now reference updated type
# → No need to find and update individual instances
```

### 2. Memory Efficiency
```python
# 10,000 swords across all stories
# Old way: 10,000 × 200 bytes = 2MB
# New way: 1 × 200 bytes + 10,000 × 24 bytes = ~240KB
```

### 3. Centralized Logic
```python
# Define behavior once on singleton
class WearableAsset(Singleton):
    def put_on(self):
        self.times_worn += 1
        # Complex logic here, shared by all tokens
```

### 4. Query Type Properties
```python
# Get all swords with damage > 20
powerful_swords = [
    label for label, asset in WearableAsset.all_instances()
    if asset.damage > 20
]

# Create tokens for these
for label in powerful_swords:
    token = Wearable(label, graph=graph)
```

---

## Implementation Questions

### Q1: Where do SingletonNodes live?

**Option A**: In graph, linked to owner
```python
my_sword = Wearable('iron_sword', graph=story_graph)
player.inventory.add(my_sword)
# sword.uid in graph.nodes
# Edge from player → sword
```

**Option B**: In registry, referenced by owner
```python
my_sword = Wearable('iron_sword')  # No graph
player.inventory[my_sword.uid] = my_sword
# Not in graph.nodes, just in player's dict
```

**Recommendation**: Option A (in graph) for consistency with other nodes.

### Q2: How to handle countable assets (potions)?

```python
class CountableAsset(Singleton):
    """Asset that can be stacked."""
    stack_size: int = 99

# In player inventory
class Wallet:
    counts: dict[UUID, int]  # asset_type_uid → count
    
    def add(self, asset_type: Singleton, count: int = 1):
        self.counts[asset_type.uid] = \
            self.counts.get(asset_type.uid, 0) + count
    
    def has(self, asset_type: Singleton, count: int = 1) -> bool:
        return self.counts.get(asset_type.uid, 0) >= count
```

### Q3: What about durability/condition?

**Instance var approach** (your current):
```python
class WearableAsset(Singleton):
    condition: float = Field(1.0, json_schema_extra={"is_instance_var": True})

my_sword = Wearable('iron_sword')
my_sword.condition = 0.5  # This sword is damaged
```

**Alternative: Locals approach**:
```python
my_sword = Wearable('iron_sword')
my_sword.locals['condition'] = 0.5
```

**Recommendation**: Instance vars (explicit schema, type-safe).

---

## World Architecture Update

```python
class World(Singleton):
    def __init__(
        self,
        label: str,
        script_manager: ScriptManager,
        domain_manager: DomainManager,
        asset_manager: AssetManager,      # NEW
        resource_manager: ResourceManager  # NEW
    ):
        super().__init__(label=label)
        self.script_manager = script_manager
        self.domain_manager = domain_manager
        self.asset_manager = asset_manager
        self.resource_manager = resource_manager
        
        # Load assets from script
        for asset_config in script_manager.get_assets():
            self.asset_manager.load_assets_from_file(
                asset_config['asset_type'],
                asset_config['source']
            )
```

---

## Testing Strategy

```python
def test_singleton_asset_pattern():
    """Test type/token separation."""
    
    # Setup asset type
    class TestAsset(Singleton):
        desc: str
        value: int
        uses: int = Field(0, json_schema_extra={"is_instance_var": True})
    
    TestAsset(label='sword', desc='A sword', value=50)
    
    # Create tokens
    graph = Graph(label='test')
    token1 = Token[TestAsset]('sword', graph=graph)
    token2 = Token[TestAsset]('sword', graph=graph)
    
    # Type properties are shared
    assert token1.desc == token2.desc == "A sword"
    assert token1.value == token2.value == 50
    
    # Instance properties are independent
    token1.uses += 1
    assert token1.uses == 1
    assert token2.uses == 0
    
    # Singleton unchanged
    assert TestAsset.get_instance('sword').uses == 0


def test_asset_manager_integration():
    """Test asset manager in world."""
    
    asset_manager = AssetManager()
    asset_manager.register_asset_class('weapons', WeaponAsset)
    asset_manager.load_assets_from_file('weapons', 'test_weapons.yaml')
    
    # Create world
    world = World(
        label='test_world',
        script_manager=script_manager,
        asset_manager=asset_manager
    )
    
    # Create story
    story = world.create_story('test_story')
    
    # Create token
    sword = asset_manager.create_token('weapons', 'iron_sword', story)
    
    assert sword.desc == "A sturdy iron blade"
    assert sword.damage == 15
    assert sword.times_used == 0
```

---

## Summary

**Three Manager Pattern**:
1. **ScriptManager**: Story templates (scenes, blocks)
2. **AssetManager**: Singleton game assets (items, abilities)
3. **ResourceManager**: File-based media (images, audio)

**Four Manager Pattern** (Including Domain):
1. **ScriptManager**: Story templates
2. **DomainManager**: Custom classes/handlers
3. **AssetManager**: Singleton game assets
4. **ResourceManager**: File-based media

**Type/Token Pattern**:
- **Singleton**: Immutable type definition, globally shared
- **Token**: Mutable token, wraps singleton, independent state
- **Benefits**: Consistency, memory efficiency, centralized updates

This pattern explains your singleton obsession perfectly. It's not just for uniqueness - it's for **shared type identity with independent instance state**.
