# StoryTangl MVP: Script-to-Graph Implementation Plan

## Overview

**Goal**: Enable full story creation from YAML IR scripts using four-manager World architecture with complete graph materialization.

**Success Criteria**: 
- Load YAML script → Create World → Instantiate StoryGraph → Navigate with cursor
- Test with CLI playthrough
- All tests passing

---

## Phase 1: Manager Foundation

### 1.1 Create DomainManager Class

**Location**: `tangl/story/story_domain/domain_manager.py`

**What**: Class registry and handler management for custom story classes.

**Why**: Need to resolve `obj_cls` strings in scripts to actual Python classes (e.g., "Elf" → Elf class).

**How**:
```python
class DomainManager:
    """Manages custom classes and handlers for a story world."""
    
    def __init__(self):
        self.class_registry: dict[str, Type] = {}
        self.dispatch_registry = DispatchRegistry(label='domain_handlers')
    
    def register_class(self, name: str, cls: Type):
        """Register custom class (e.g., 'Elf' → Elf class)."""
        self.class_registry[name] = cls
    
    def resolve_class(self, obj_cls_str: Optional[str]) -> Type:
        """
        Resolve obj_cls string to actual class.
        
        Priority:
        1. Custom registry ('Elf' → registered Elf class)
        2. Qualified import ('tangl.story.Actor' → import and return)
        3. Fallback to Node
        """
        if not obj_cls_str:
            return Node
        
        # Check custom registry
        if obj_cls_str in self.class_registry:
            return self.class_registry[obj_cls_str]
        
        # Try import
        try:
            module_path, class_name = obj_cls_str.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ValueError, ImportError, AttributeError):
            logger.warning(f"Could not resolve {obj_cls_str}, using Node")
            return Node
    
    def load_domain_module(self, module_path: str):
        """
        Import module and auto-register Entity subclasses.
        
        Example:
        domain.load_domain_module('my_story.custom_classes')
        # Auto-registers Elf, Dragon, etc.
        """
        module = importlib.import_module(module_path)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Entity) and obj is not Entity:
                self.register_class(name, obj)
```

**Test**:
```python
# test_domain_manager.py
def test_resolve_builtin_class():
    domain = DomainManager()
    cls = domain.resolve_class('tangl.story.Actor')
    assert cls is Actor

def test_resolve_custom_class():
    class Elf(Actor):
        pass
    
    domain = DomainManager()
    domain.register_class('Elf', Elf)
    
    cls = domain.resolve_class('Elf')
    assert cls is Elf

def test_resolve_fallback():
    domain = DomainManager()
    cls = domain.resolve_class('NonexistentClass')
    assert cls is Node
```

**Verification**: Run tests, all pass.

---

### 1.2 Create AssetManager Class

**Location**: `tangl/story/fabula/asset/asset_manager.py`

**What**: Registry and factory for singleton asset types (Discrete/Countable).

**Why**: Scripts reference assets by type and label; need to load definitions and create tokens.

**How**:
```python
class AssetManager:
    """Manages singleton asset types for game economy."""
    
    def __init__(self):
        self.asset_classes: dict[str, Type[AssetType]] = {}
    
    def register_asset_class(self, name: str, cls: Type[AssetType]):
        """Register asset type class."""
        self.asset_classes[name] = cls
    
    def load_from_file(self, asset_type: str, filepath: Path):
        """Load asset instances from YAML."""
        cls = self.asset_classes[asset_type]
        cls.load_instances(filepath)
    
    def load_from_data(self, asset_type: str, data: list[dict]):
        """Load asset instances from parsed data."""
        cls = self.asset_classes[asset_type]
        for item_data in data:
            cls.structure(item_data)
    
    def create_token(
        self,
        asset_type: str,
        label: str,
        graph: Graph
    ) -> DiscreteAsset:
        """Create wrapped token for discrete asset."""
        cls = self.asset_classes[asset_type]
        wrapper_cls = DiscreteAsset[cls]
        return wrapper_cls(label, graph=graph)
    
    def get_asset_type(self, asset_type: str, label: str) -> AssetType:
        """Get singleton type definition."""
        cls = self.asset_classes[asset_type]
        return cls.get_instance(label)
```

**Test**:
```python
# test_asset_manager.py
def test_load_and_create_tokens():
    class TestAsset(AssetType):
        value: int
    
    manager = AssetManager()
    manager.register_asset_class('test', TestAsset)
    manager.load_from_data('test', [
        {'label': 'sword', 'value': 50}
    ])
    
    # Get type
    sword_type = manager.get_asset_type('test', 'sword')
    assert sword_type.value == 50
    
    # Create token
    graph = Graph(label='test')
    token = manager.create_token('test', 'sword', graph)
    assert token.singleton.value == 50
```

**Verification**: Run tests, verify tokens created correctly.

---

### 1.3 Create ResourceManager Class

**Location**: `tangl/media/resource_manager.py`

**What**: Media file indexing and URL generation.

**Why**: Scripts reference media files; need to track RITs and serve URLs.

**How**:
```python
class ResourceManager:
    """Manages file-based media resources."""
    
    def __init__(self, resource_path: Path):
        self.resource_path = resource_path
        self.registry = MediaResourceRegistry(label='world_media')
    
    def index_directory(self, subdir: str = 'images') -> list[MediaRIT]:
        """Index all files in subdirectory."""
        path = self.resource_path / subdir
        if not path.exists():
            return []
        files = list(path.glob('*'))
        return self.registry.index(files)
    
    def get_rit(self, alias: str) -> Optional[MediaRIT]:
        """Look up RIT by name or content hash."""
        return self.registry.find_one(alias=alias)
    
    def get_url(self, rit: MediaRIT) -> str:
        """Generate URL for frontend."""
        return f"/assets/{rit.content_hash[:16]}.{rit.extension}"
```

**Test**:
```python
# test_resource_manager.py
def test_index_and_lookup(tmp_path):
    # Create test file
    img_dir = tmp_path / 'images'
    img_dir.mkdir()
    (img_dir / 'test.png').write_bytes(b'fake image data')
    
    manager = ResourceManager(tmp_path)
    rits = manager.index_directory('images')
    
    assert len(rits) == 1
    rit = manager.get_rit('test.png')
    assert rit is not None
    assert rit.content_hash is not None
```

**Verification**: Run tests, verify RITs created and lookups work.

---

### 1.4 Update World Class

**Location**: `tangl/story/story_domain/world.py`

**What**: Add four-manager architecture to World.

**Why**: World needs to coordinate all managers for story creation.

**How**:
```python
class World(Singleton):
    """Story world containing templates, handlers, and resources."""
    
    def __init__(
        self,
        label: str,
        script_manager: ScriptManager,
        domain_manager: Optional[DomainManager] = None,
        asset_manager: Optional[AssetManager] = None,
        resource_manager: Optional[ResourceManager] = None
    ):
        super().__init__(label=label)
        self.script_manager = script_manager
        self.domain_manager = domain_manager or DomainManager()
        self.asset_manager = asset_manager or AssetManager()
        self.resource_manager = resource_manager or ResourceManager(Path('.'))
        
        # Setup default asset classes
        self._setup_default_assets()
    
    def _setup_default_assets(self):
        """Register built-in asset types."""
        from tangl.story.fabula.asset import (
            CountableAsset,
            DiscreteAsset,
        )
        # Register if not already registered
        if 'countable' not in self.asset_manager.asset_classes:
            self.asset_manager.register_asset_class(
                'countable',
                CountableAsset
            )
    
    def create_story(
        self,
        story_label: str,
        mode: str = 'full'
    ) -> StoryGraph:
        """Create new story instance."""
        if mode == 'full':
            return self._create_story_full(story_label)
        else:
            raise NotImplementedError(f"Mode {mode} not yet implemented")
    
    def _create_story_full(self, story_label: str) -> StoryGraph:
        """MVP: Full materialization (implemented in Phase 2)."""
        raise NotImplementedError("To be implemented in Phase 2")
```

**Test**:
```python
# test_world_setup.py
def test_world_creation():
    script_data = {
        'label': 'test',
        'metadata': {'title': 'Test', 'author': 'Test'},
        'scenes': {'intro': {'blocks': {'start': {}}}}
    }
    sm = ScriptManager.from_data(script_data)
    world = World(label='test_world', script_manager=sm)
    
    assert world.script_manager is not None
    assert world.domain_manager is not None
    assert world.asset_manager is not None
    assert world.resource_manager is not None
```

**Verification**: World instantiates with all managers.

---

## Phase 2: Script-to-Graph Materialization

### 2.1 Implement Node Building Helpers

**Location**: `tangl/story/story_domain/world.py` (add methods to World)

**What**: Methods to instantiate nodes from script templates.

**Why**: Need to convert script dicts to graph nodes.

**How**:
```python
# In World class:

def _build_actors(self, graph: StoryGraph) -> dict[str, UUID]:
    """Instantiate all actors from script."""
    node_map = {}
    
    for actor_data in self.script_manager.get_unstructured('actors'):
        obj_cls = self.domain_manager.resolve_class(
            actor_data.get('obj_cls')
        )
        
        actor = obj_cls.structure(actor_data, graph=graph)
        node_map[actor.label] = actor.uid
    
    return node_map

def _build_locations(self, graph: StoryGraph) -> dict[str, UUID]:
    """Instantiate all locations from script."""
    node_map = {}
    
    for location_data in self.script_manager.get_unstructured('locations'):
        obj_cls = self.domain_manager.resolve_class(
            location_data.get('obj_cls')
        )
        
        location = obj_cls.structure(location_data, graph=graph)
        node_map[location.label] = location.uid
    
    return node_map

def _build_blocks(
    self,
    graph: StoryGraph
) -> dict[str, UUID]:
    """
    Instantiate all blocks from all scenes.
    
    Returns dict with qualified labels: 'scene.block' → uid
    """
    node_map = {}
    
    scenes = self.script_manager.master_script.scenes
    
    # Handle both dict and list formats
    if isinstance(scenes, list):
        scenes = {s['label']: s for s in scenes}
    
    for scene_label, scene_data in scenes.items():
        blocks = scene_data.get('blocks', {})
        
        # Handle both dict and list formats
        if isinstance(blocks, list):
            blocks = {b['label']: b for b in blocks}
        
        for block_label, block_data in blocks.items():
            qualified_label = f"{scene_label}.{block_label}"
            
            obj_cls = self.domain_manager.resolve_class(
                block_data.get('block_cls') or block_data.get('obj_cls')
            )
            
            # Store action scripts for later edge creation
            block_data_copy = block_data.copy()
            action_scripts = {
                'actions': block_data_copy.pop('actions', []),
                'continues': block_data_copy.pop('continues', []),
                'redirects': block_data_copy.pop('redirects', [])
            }
            
            block = obj_cls.structure(block_data_copy, graph=graph)
            
            # Store action scripts in locals for edge building
            block.locals['_action_scripts'] = action_scripts
            
            node_map[qualified_label] = block.uid
    
    return node_map

def _build_scenes(
    self,
    graph: StoryGraph,
    node_map: dict[str, UUID]
) -> dict[str, UUID]:
    """Instantiate all scenes with member references."""
    scene_map = {}
    
    scenes = self.script_manager.master_script.scenes
    if isinstance(scenes, list):
        scenes = {s['label']: s for s in scenes}
    
    for scene_label, scene_data in scenes.items():
        # Collect member UIDs from blocks
        blocks = scene_data.get('blocks', {})
        if isinstance(blocks, list):
            blocks = {b['label']: b for b in blocks}
        
        member_uids = []
        for block_label in blocks.keys():
            qualified_label = f"{scene_label}.{block_label}"
            member_uids.append(node_map[qualified_label])
        
        obj_cls = self.domain_manager.resolve_class(
            scene_data.get('obj_cls')
        )
        
        scene = obj_cls.structure(
            scene_data,
            graph=graph,
            member_ids=member_uids
        )
        scene_map[scene_label] = scene.uid
    
    return scene_map
```

**Test**:
```python
# test_node_building.py
def test_build_actors():
    script_data = {
        'label': 'test',
        'metadata': {'title': 'Test', 'author': 'Test'},
        'actors': {
            'alice': {'name': 'Alice'},
            'bob': {'name': 'Bob'}
        },
        'scenes': {'intro': {'blocks': {'start': {}}}}
    }
    sm = ScriptManager.from_data(script_data)
    world = World(label='test', script_manager=sm)
    graph = StoryGraph(label='test_story', world=world)
    
    node_map = world._build_actors(graph)
    
    assert 'alice' in node_map
    assert 'bob' in node_map
    assert len(graph.nodes) == 2
```

**Verification**: Nodes created in graph with correct labels.

---

### 2.2 Implement Edge Building Helpers

**Location**: `tangl/story/story_domain/world.py`

**What**: Methods to create ActionEdges from block action scripts.

**Why**: Need to link blocks together for navigation.

**How**:
```python
# In World class:

def _resolve_successor(
    self,
    successor: str,
    current_scene: str,
    node_map: dict[str, UUID]
) -> UUID:
    """
    Resolve successor reference to UID.
    
    Supports:
    - 'block' (same scene) → 'scene.block'
    - 'scene.block' (fully qualified)
    - 'scene' (scene reference, use first block)
    """
    # Try as-is first (fully qualified or scene-level)
    if successor in node_map:
        return node_map[successor]
    
    # Try with current scene prefix
    qualified = f"{current_scene}.{successor}"
    if qualified in node_map:
        return node_map[qualified]
    
    # Try as scene reference (get first block)
    scenes = self.script_manager.master_script.scenes
    if isinstance(scenes, list):
        scenes = {s['label']: s for s in scenes}
    
    if successor in scenes:
        scene_data = scenes[successor]
        blocks = scene_data.get('blocks', {})
        if isinstance(blocks, list):
            first_block_label = blocks[0]['label']
        else:
            first_block_label = next(iter(blocks.keys()))
        
        qualified = f"{successor}.{first_block_label}"
        if qualified in node_map:
            return node_map[qualified]
    
    raise ValueError(f"Could not resolve successor: {successor}")

def _build_action_edges(
    self,
    graph: StoryGraph,
    node_map: dict[str, UUID]
):
    """Create ActionEdges from block action scripts."""
    
    scenes = self.script_manager.master_script.scenes
    if isinstance(scenes, list):
        scenes = {s['label']: s for s in scenes}
    
    for scene_label, scene_data in scenes.items():
        blocks = scene_data.get('blocks', {})
        if isinstance(blocks, list):
            blocks = {b['label']: b for b in blocks}
        
        for block_label, block_data in blocks.items():
            qualified_label = f"{scene_label}.{block_label}"
            source_uid = node_map[qualified_label]
            
            # Get stored action scripts
            block = graph.get(source_uid)
            action_scripts = block.locals.get('_action_scripts', {})
            
            # Process all action types
            for action_list in [
                action_scripts.get('actions', []),
                action_scripts.get('continues', []),
                action_scripts.get('redirects', [])
            ]:
                for action_data in action_list:
                    dest_uid = self._resolve_successor(
                        action_data['successor'],
                        scene_label,
                        node_map
                    )
                    
                    # Resolve edge class
                    edge_cls = self.domain_manager.resolve_class(
                        action_data.get('obj_cls')
                    )
                    if edge_cls is Node:  # Fallback didn't work
                        from tangl.story.episodic_process import ActionEdge
                        edge_cls = ActionEdge
                    
                    edge_cls.structure(
                        action_data,
                        graph=graph,
                        source_id=source_uid,
                        destination_id=dest_uid
                    )
            
            # Clean up temporary data
            del block.locals['_action_scripts']
```

**Test**:
```python
# test_edge_building.py
def test_build_action_edges():
    script_data = {
        'label': 'test',
        'metadata': {'title': 'Test', 'author': 'Test'},
        'scenes': {
            'intro': {
                'blocks': {
                    'start': {
                        'content': 'Beginning',
                        'actions': [
                            {
                                'text': 'Continue',
                                'successor': 'next'
                            }
                        ]
                    },
                    'next': {
                        'content': 'Next part'
                    }
                }
            }
        }
    }
    
    sm = ScriptManager.from_data(script_data)
    world = World(label='test', script_manager=sm)
    graph = StoryGraph(label='test_story', world=world)
    
    # Build nodes
    node_map = world._build_blocks(graph)
    
    # Build edges
    world._build_action_edges(graph, node_map)
    
    # Verify edge exists
    start_uid = node_map['intro.start']
    edges = list(graph.find_edges(source_id=start_uid))
    assert len(edges) == 1
    assert edges[0].text == 'Continue'
```

**Verification**: Edges created between blocks.

---

### 2.3 Implement Full Materialization

**Location**: `tangl/story/story_domain/world.py`

**What**: Complete `_create_story_full()` method.

**Why**: Entry point for MVP story creation.

**How**:
```python
# In World class:

def _create_story_full(self, story_label: str) -> StoryGraph:
    """
    MVP: Build entire graph upfront.
    
    Process:
    1. Create graph
    2. Instantiate all nodes (actors, locations, blocks, scenes)
    3. Create all edges (actions, roles, settings)
    4. Set initial cursor
    """
    graph = StoryGraph(label=story_label, world=self)
    
    # Phase 1: Concept nodes (no dependencies)
    node_map = {}
    node_map.update(self._build_actors(graph))
    node_map.update(self._build_locations(graph))
    # Assets handled separately if needed
    
    # Phase 2: Structure nodes
    node_map.update(self._build_blocks(graph))
    node_map.update(self._build_scenes(graph, node_map))
    
    # Phase 3: Edges
    self._build_action_edges(graph, node_map)
    # Role/setting edges TODO if needed for MVP
    
    # Phase 4: Set cursor
    start_scene, start_block = self._get_starting_cursor()
    start_label = f"{start_scene}.{start_block}"
    start_uid = node_map[start_label]
    
    from tangl.vm import Frame
    graph.cursor = Frame(graph=graph, cursor_id=start_uid)
    
    return graph

def _get_starting_cursor(self) -> tuple[str, str]:
    """
    Get starting scene and block labels.
    
    Priority:
    1. metadata.start_at field
    2. First scene, first block
    """
    # Check for explicit start
    metadata = self.script_manager.get_story_metadata()
    start_at = metadata.get('start_at')
    
    if start_at:
        if '.' in start_at:
            scene, block = start_at.split('.', 1)
            return scene, block
        else:
            # Just scene, get first block
            scenes = self.script_manager.master_script.scenes
            if isinstance(scenes, list):
                scene_data = next(s for s in scenes if s['label'] == start_at)
            else:
                scene_data = scenes[start_at]
            
            blocks = scene_data.get('blocks', {})
            if isinstance(blocks, list):
                first_block = blocks[0]['label']
            else:
                first_block = next(iter(blocks.keys()))
            
            return start_at, first_block
    
    # Default: first scene, first block
    scenes = self.script_manager.master_script.scenes
    if isinstance(scenes, list):
        first_scene = scenes[0]['label']
        first_scene_data = scenes[0]
    else:
        first_scene = next(iter(scenes.keys()))
        first_scene_data = scenes[first_scene]
    
    blocks = first_scene_data.get('blocks', {})
    if isinstance(blocks, list):
        first_block = blocks[0]['label']
    else:
        first_block = next(iter(blocks.keys()))
    
    return first_scene, first_block
```

**Test**:
```python
# test_full_materialization.py
def test_create_story_full():
    script_data = {
        'label': 'test',
        'metadata': {'title': 'Test', 'author': 'Test'},
        'scenes': {
            'intro': {
                'blocks': {
                    'start': {
                        'content': 'You begin.',
                        'actions': [
                            {'text': 'Go north', 'successor': 'forest.entrance'}
                        ]
                    }
                }
            },
            'forest': {
                'blocks': {
                    'entrance': {'content': 'You enter the forest.'}
                }
            }
        }
    }
    
    sm = ScriptManager.from_data(script_data)
    world = World(label='test', script_manager=sm)
    
    story = world.create_story('player_story')
    
    # Verify graph created
    assert story.label == 'player_story'
    assert len(story.nodes) >= 2  # At least 2 blocks
    
    # Verify cursor set
    assert story.cursor is not None
    assert story.cursor.cursor.label == 'start'
    
    # Verify navigation works
    actions = story.cursor.get_available_actions()
    assert len(actions) == 1
    assert actions[0].text == 'Go north'
```

**Verification**: Full story graph created and navigable.

---

## Phase 3: ScriptManager Updates

### 3.1 Add Helper Methods to ScriptManager

**Location**: `tangl/ir/script_manager.py`

**What**: Convenience methods for accessing script data.

**Why**: World needs clean interface to script data.

**How**:
```python
# In ScriptManager class:

def get_story_metadata(self) -> dict:
    """Get metadata dict."""
    return self.master_script.metadata.model_dump()

def get_story_globals(self) -> dict:
    """Get global variables dict."""
    return self.master_script.locals or {}

def get_unstructured(self, key: str) -> Iterator[dict]:
    """
    Get unstructured data for a key.
    
    Handles both list and dict formats, yields dicts.
    """
    if not hasattr(self.master_script, key):
        return
    
    data = getattr(self.master_script, key)
    if not data:
        return
    
    if isinstance(data, dict):
        for label, item in data.items():
            yield item.model_dump()
    elif isinstance(data, list):
        for item in data:
            yield item.model_dump()
```

**Test**:
```python
# test_script_manager_helpers.py
def test_get_unstructured_dict():
    script_data = {
        'label': 'test',
        'metadata': {'title': 'Test', 'author': 'Test'},
        'actors': {
            'alice': {'name': 'Alice'},
            'bob': {'name': 'Bob'}
        },
        'scenes': {'intro': {'blocks': {'start': {}}}}
    }
    
    sm = ScriptManager.from_data(script_data)
    actors = list(sm.get_unstructured('actors'))
    
    assert len(actors) == 2
    assert actors[0]['label'] == 'alice'

def test_get_unstructured_list():
    script_data = {
        'label': 'test',
        'metadata': {'title': 'Test', 'author': 'Test'},
        'actors': [
            {'label': 'alice', 'name': 'Alice'},
            {'label': 'bob', 'name': 'Bob'}
        ],
        'scenes': {'intro': {'blocks': {'start': {}}}}
    }
    
    sm = ScriptManager.from_data(script_data)
    actors = list(sm.get_unstructured('actors'))
    
    assert len(actors) == 2
```

**Verification**: Both dict and list formats work.

---

## Phase 4: Integration Testing

### 4.1 Create Integration Test Suite

**Location**: `tests/story/test_script_to_graph_integration.py`

**What**: End-to-end tests of script → world → story → navigation.

**Why**: Verify complete pipeline works.

**How**:
```python
def test_complete_story_creation():
    """Test full pipeline from script to navigation."""
    
    script_data = {
        'label': 'crossroads_demo',
        'metadata': {
            'title': 'The Crossroads',
            'author': 'Test Author'
        },
        'scenes': {
            'crossroads': {
                'blocks': {
                    'start': {
                        'content': 'You stand at a crossroads.',
                        'actions': [
                            {
                                'text': 'Take the left path',
                                'successor': 'garden.entrance'
                            },
                            {
                                'text': 'Take the right path',
                                'successor': 'cave.entrance'
                            }
                        ]
                    }
                }
            },
            'garden': {
                'blocks': {
                    'entrance': {
                        'content': 'A peaceful garden.'
                    }
                }
            },
            'cave': {
                'blocks': {
                    'entrance': {
                        'content': 'A dark cave.'
                    }
                }
            }
        }
    }
    
    # Create world
    sm = ScriptManager.from_data(script_data)
    world = World(label='test_world', script_manager=sm)
    
    # Create story
    story = world.create_story('test_story')
    
    # Verify initial state
    frame = story.cursor
    content = frame.journal()
    assert 'crossroads' in content.lower()
    
    # Verify choices
    actions = frame.get_available_actions()
    assert len(actions) == 2
    assert actions[0].text == 'Take the left path'
    
    # Navigate
    frame.traverse_to(0)
    
    # Verify new location
    content = frame.journal()
    assert 'garden' in content.lower()

def test_with_actors():
    """Test story with actors."""
    
    script_data = {
        'label': 'actor_test',
        'metadata': {'title': 'Test', 'author': 'Test'},
        'actors': {
            'alice': {'name': 'Alice'},
            'bob': {'name': 'Bob'}
        },
        'scenes': {
            'intro': {
                'blocks': {
                    'start': {
                        'content': 'You meet Alice and Bob.'
                    }
                }
            }
        }
    }
    
    sm = ScriptManager.from_data(script_data)
    world = World(label='test', script_manager=sm)
    story = world.create_story('test')
    
    # Verify actors created
    alice = story.find(label='alice')
    assert alice is not None
    assert alice.name == 'Alice'

def test_with_custom_class():
    """Test story with custom actor class."""
    
    class Elf(Actor):
        elf_magic: int = 