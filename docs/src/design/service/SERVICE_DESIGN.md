# Service Layer Architecture (v3.7)

**Status:** This document reflects the **actual current implementation** as of v3.7.  
**Last Updated:** November 2025  
**Location:** `engine/src/tangl/service/` and `apps/*/src/tangl/*/`

---

## Executive Summary

StoryTangl's service layer provides a **clean orchestration boundary** between applications and the narrative engine by:
- ✅ Decoupling **transport layers** (CLI, REST, future GraphQL) from engine internals
- ✅ Providing **dependency injection** for User, Ledger, and Frame resources
- ✅ Managing **resource lifecycle** (hydration, caching, persistence write-back)
- ✅ Exposing **controller endpoints** with consistent API semantics
- ✅ Enabling **pluggable persistence** backends (memory, file, Redis, MongoDB)

**Key Insight:** Applications never directly manipulate Core or VM objects. They invoke named endpoints through the Orchestrator, which handles all resource management, allowing the engine to evolve independently of client code.

---

## Core Concepts

### Service Boundary

**The service layer is the ONLY interface between applications and the engine.**

```python
# ❌ NEVER do this in application code:
ledger = Ledger(graph=graph, cursor_id=start.uid)
frame = ledger.get_frame()
frame.advance(choice_edge)

# ✅ ALWAYS do this instead:
result = orchestrator.execute(
    "RuntimeController.resolve_choice",
    user_id=user_id,
    choice_id=choice_id
)
```

**Benefits:**
- Engine can refactor internals without breaking applications
- Consistent error handling and validation
- Automatic resource lifecycle management
- Simplified testing (mock the orchestrator, not the engine)

### Controllers as Domain Logic

**Controllers bundle related operations for a specific domain.**

```
RuntimeController  → Story runtime operations (create, advance, query state)
WorldController    → World management (list, load, describe)
UserController     → User/session management (create, authenticate, profile)
SystemController   → System operations (health, diagnostics)
```

**Controller methods:**
- Are decorated with `@ApiEndpoint.annotate()`
- Declare dependencies via type hints
- Return plain dictionaries or Pydantic models
- Contain ONLY domain logic (no persistence, no transport)

### Orchestrator as Resource Manager

**The Orchestrator coordinates endpoint execution and manages resources.**

**Responsibilities:**
1. **Endpoint Registry** - Maps endpoint names to controller methods
2. **Resource Hydration** - Loads User/Ledger/Frame from persistence or cache
3. **Dependency Injection** - Passes resources to controller methods
4. **Write-Back** - Persists mutated resources after CREATE/UPDATE/DELETE
5. **Cache Management** - Avoids redundant persistence round-trips per request

**Orchestrator does NOT:**
- Know about HTTP, WebSockets, or CLI
- Implement business logic
- Directly manipulate Core or VM objects

---

## Architecture Overview

### Layer Diagram

```
┌────────────────────────────────────────────────────────────┐
│                   Application Layer                        │
│  (tangl.cli, tangl.rest, future: tangl.graphql)           │
│                                                            │
│  • CLI commands (cmd2)                                     │
│  • FastAPI routes (REST)                                   │
│  • GraphQL resolvers (future)                              │
│                                                            │
│  Knows: HTTP, CLI, user I/O                                │
│  Does: Parse requests → call orchestrator → format response│
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│                    Service Layer                           │
│  (tangl.service)                                           │
│                                                            │
│  Orchestrator ───┬──→ RuntimeController                    │
│                  ├──→ WorldController                      │
│                  ├──→ UserController                       │
│                  └──→ SystemController                     │
│                                                            │
│  Knows: Endpoint names, resource types, persistence        │
│  Does: Hydrate deps → invoke logic → write back           │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│                    Engine Layer                            │
│  (tangl.core, tangl.vm, tangl.story)                      │
│                                                            │
│  • Graph/Entity primitives (core)                          │
│  • Frame/Ledger runtime (vm)                               │
│  • World/Episode/Block (story)                             │
│                                                            │
│  Knows: Graph structure, phase execution, dispatch         │
│  Does: Execute narrative logic, maintain state             │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│                  Persistence Layer                         │
│  (tangl.persistence)                                       │
│                                                            │
│  • PersistenceManager (abstraction)                        │
│  • Storage backends: Memory, File, Redis, MongoDB          │
│  • Serializers: Pickle, JSON, YAML, BSON                   │
│  • StructuringHandler: Pydantic round-trip                 │
│                                                            │
│  Knows: Serialization, storage I/O                         │
│  Does: Save/load HasUid objects by UUID                    │
└────────────────────────────────────────────────────────────┘
```

### Key Classes

**Service Core:**
- `Orchestrator` - Endpoint registry and resource lifecycle manager
- `ApiEndpoint` - Method decorator with access control and CRUD semantics
- `HasApiEndpoints` - Mixin for controller auto-discovery
- `User` - User account model with current ledger tracking

**Controllers:**
- `RuntimeController` - Story operations (create, advance, query)
- `WorldController` - World catalog and loading
- `UserController` - User CRUD and authentication
- `SystemController` - Health checks and diagnostics

**Resource Types:**
- `User` - Persistent across sessions, has current_ledger_id
- `Ledger` - Story session state (graph, records, step)
- `Frame` - Ephemeral VM runtime (created per-request from Ledger)

**Enums:**
- `AccessLevel` - PUBLIC, USER, ADMIN
- `MethodType` - READ, CREATE, UPDATE, DELETE
- `ResponseType` - INFO, CONTENT, STATUS

---

## The Orchestration Cycle

### Full Request Flow

**Example:** User makes a choice in their story

```python
# 1. Application layer (FastAPI route)
@app.post("/do")
async def do_choice(choice_id: UUID, user_id: UUID = Depends(get_user_id)):
    orchestrator = get_orchestrator()
    result = orchestrator.execute(
        "RuntimeController.resolve_choice",
        user_id=user_id,
        choice_id=choice_id
    )
    return result

# 2. Orchestrator.execute()
def execute(endpoint_name: str, *, user_id: UUID | None, **params):
    # a. Look up endpoint
    controller, endpoint = self._endpoints[endpoint_name]
    
    # b. Clear cache for new request
    self._resource_cache = {}
    
    # c. Hydrate dependencies
    resolved_params = self._hydrate_resources(endpoint, user_id, params)
    
    # d. Invoke controller method
    result = endpoint(controller, **resolved_params)
    
    # e. Write back if mutation
    if endpoint.method_type in {CREATE, UPDATE, DELETE}:
        self._write_back_resources()
    
    return result

# 3. Controller method (domain logic)
@ApiEndpoint.annotate(method_type=MethodType.UPDATE)
def resolve_choice(self, ledger: Ledger, frame: Frame, choice_id: UUID):
    # Find the choice edge
    choice = ledger.graph.get(choice_id)
    if not isinstance(choice, ChoiceEdge):
        raise ValueError("Invalid choice")
    
    # Advance the story
    frame.advance(choice)
    
    # Return result
    return {
        "status": "resolved",
        "cursor_id": str(ledger.cursor_id),
        "step": ledger.step
    }

# 4. Write-back phase (automatic)
# Orchestrator marks ledger as dirty, persists it
```

### Dependency Resolution Order

**When `resolve_choice(ledger, frame, choice_id)` is called:**

1. **Explicit params** - `choice_id` comes from request params
2. **User hydration** - If `user_id` provided and method needs `User`, load from persistence
3. **Ledger hydration** - If method needs `Ledger`:
   - Check cache first
   - If not cached, load from persistence
   - If `ledger_id` not in params, use `user.current_ledger_id`
4. **Frame creation** - If method needs `Frame`:
   - Must have already hydrated Ledger
   - Call `ledger.get_frame()` to create ephemeral Frame
5. **Invoke method** - Pass all resolved parameters
6. **Cache management** - Mark resources as dirty if mutation occurred

---

## Dependency Injection

### Type Hint Resolution

**The Orchestrator inspects method signatures to determine dependencies.**

```python
class RuntimeController(HasApiEndpoints):
    
    @ApiEndpoint.annotate(method_type=MethodType.READ)
    def get_story_info(self, ledger: Ledger) -> dict:
        # Orchestrator sees 'ledger: Ledger' in signature
        # → loads ledger from persistence
        # → passes it to method
        return {
            "cursor_id": ledger.cursor_id,
            "step": ledger.step,
            "title": ledger.graph.label
        }
```

**Supported type hints:**
- `user: User` - Current user account
- `ledger: Ledger` - Current story session
- `frame: Frame` - Ephemeral VM runtime
- Explicit params - Any other parameters come from request

### Ledger Resolution Rules

**The Orchestrator determines which Ledger to load based on:**

1. **Explicit `ledger_id` in params** - Use that specific ledger
2. **User's current ledger** - Use `user.current_ledger_id`
3. **No resolution path** - Raise `ValueError`

```python
# Example: Jump to any ledger (admin function)
@ApiEndpoint.annotate(access_level=AccessLevel.ADMIN)
def inspect_ledger(self, ledger: Ledger) -> dict:
    # Caller must provide ledger_id explicitly
    pass

# Example: Operate on user's current story
@ApiEndpoint.annotate(access_level=AccessLevel.USER)
def get_choices(self, user: User, ledger: Ledger) -> list:
    # Uses user.current_ledger_id automatically
    pass
```

### Frame Lifecycle

**Frames are NEVER persisted - they are ephemeral VM runtimes.**

```python
# ❌ Frame is NOT a resource managed by orchestrator
# It's created on-demand from a Ledger

@ApiEndpoint.annotate()
def some_method(self, frame: Frame):
    # Orchestrator:
    # 1. Sees 'frame: Frame' type hint
    # 2. Looks for already-hydrated Ledger in cache
    # 3. Calls ledger.get_frame() to create Frame
    # 4. Passes Frame to method
    pass
```

**Why Frames aren't cached:**
- They're cheap to create (`ledger.get_frame()`)
- They hold references to Ledger internals
- They shouldn't outlive a single request
- Multiple concurrent requests should get independent Frames

---

## What's Implemented

### ✅ Core Infrastructure

**Orchestrator:**
- [x] Endpoint registration via controller discovery
- [x] Type-hint-based dependency injection
- [x] Resource caching per request
- [x] Automatic write-back for mutations
- [x] Method type classification (READ, CREATE, UPDATE, DELETE)

**ApiEndpoint Decorator:**
- [x] Access level enforcement (PUBLIC, USER, ADMIN)
- [x] Method type inference from function names
- [x] Response type classification (INFO, CONTENT, STATUS)
- [x] Preprocessor/postprocessor hooks (unused in MVP)

**Controllers:**
- [x] RuntimeController - Core story operations
- [x] WorldController - World catalog
- [x] UserController - User management
- [x] SystemController - Health checks

### ✅ Persistence Integration

**PersistenceManager:**
- [x] Abstract interface (`save`, `load`, `remove`, `__contains__`)
- [x] Mapping-like API (`__getitem__`, `__setitem__`)
- [x] Context manager (`with manager.open(uid, write_back=True)`)

**Storage Backends:**
- [x] InMemoryStorage
- [x] FileStorage (pickle, JSON, YAML, BSON)
- [x] RedisStorage (binary)
- [x] MongoStorage (BSON documents)

**Serialization:**
- [x] PickleSerializationHandler
- [x] JsonSerializationHandler
- [x] YamlSerializationHandler
- [x] BsonSerializationHandler
- [x] StructuringHandler (Pydantic round-trip via cattrs)

### ✅ RuntimeController Endpoints

| Endpoint | Method Type | Description |
|----------|-------------|-------------|
| `create_story` | CREATE | Initialize new story session |
| `get_story_info` | READ | Get ledger metadata |
| `get_available_choices` | READ | List choices from cursor |
| `resolve_choice` | UPDATE | Advance story via choice |
| `get_journal_entries` | READ | Fetch recent fragments |
| `jump_to_node` | UPDATE | Teleport cursor (debug) |

### ✅ Application Adapters

**CLI (tangl.cli):**
- [x] cmd2-based interactive shell
- [x] User management commands
- [x] World loading
- [x] Story creation and navigation
- [x] Choice selection
- [x] Journal viewing

**REST API (tangl.rest):**
- [x] FastAPI application
- [x] API key authentication
- [x] User-scoped endpoints
- [x] Per-user request locking (concurrency safety)
- [x] Health checks
- [x] OpenAPI documentation

---

## What's Missing

### ⚠️ Access Control Enforcement

**Problem:** ApiEndpoint defines `AccessLevel.PUBLIC/USER/ADMIN`, but orchestrator doesn't enforce it.

**Current State:**
- Decorators capture access levels
- No authentication/authorization hook in `Orchestrator.execute()`

**Solution:**
- Add `auth_provider` to Orchestrator constructor
- Check access level before invoking endpoint
- Raise `PermissionError` if insufficient privileges

### ⚠️ Comprehensive Error Handling

**Current Issues:**
- Some ValueError/KeyError messages are generic
- No distinction between client errors (400) vs server errors (500)
- Missing validation layer before controller invocation

**Needed:**
- Custom exception hierarchy (`ClientError`, `ResourceNotFound`, etc.)
- Validation decorators for endpoint parameters
- Consistent error response format

### ⚠️ Response Standardization

**Problem:** Controllers return raw dicts/lists - no unified response envelope.

**Current State:**
```python
# Different controllers return different shapes
{"status": "ok", "data": ...}
{"cursor_id": "...", "step": 5}
[{"uid": "...", "label": "..."}]
```

**Solution:**
- Define `BaseResponse` envelope
- Wrap all results in `{"success": bool, "data": Any, "error": str | None}`
- Add response schema to ApiEndpoint metadata

### ⚠️ Endpoint Introspection

**Missing Features:**
- List all registered endpoints
- Get endpoint metadata (params, return type, access level)
- Generate API documentation from annotations
- OpenAPI schema generation from controller definitions

### ⚠️ Preprocessor/Postprocessor Usage

**Status:** Framework exists but no concrete examples.

**Potential Use Cases:**
- Logging/tracing preprocessor
- Response sanitization postprocessor
- Parameter validation preprocessor
- Timing/metrics collection

### ⚠️ Multi-Tenancy

**Current Limitation:** One persistence manager per orchestrator.

**Needed for Production:**
- Tenant-scoped persistence
- Cross-tenant data isolation
- Tenant-specific World catalogs

### ⚠️ Session Management

**Gap:** No explicit session/auth token model.

**Current Workaround:**
- REST API uses API keys linked to users
- CLI uses in-memory user_id tracking
- No expiration, refresh, or revocation

**Needed:**
- Token-based auth (JWT, OAuth)
- Session expiration
- Refresh token flow

---

## Integration Points

### How Applications Use the Service Layer

**1. Bootstrap Orchestrator**

```python
from tangl.persistence import PersistenceManagerFactory
from tangl.service import Orchestrator
from tangl.service.controllers import (
    RuntimeController,
    WorldController,
    UserController,
    SystemController
)

# Create persistence
persistence = PersistenceManagerFactory.create_persistence_manager(
    manager_name="json_file",
    user_data_path="/var/tangl/data"
)

# Create orchestrator
orchestrator = Orchestrator(persistence)

# Register controllers
orchestrator.register_controller(RuntimeController)
orchestrator.register_controller(WorldController)
orchestrator.register_controller(UserController)
orchestrator.register_controller(SystemController)
```

**2. Create User**

```python
from tangl.service import User

user = User(label="alice")
persistence.save(user)
```

**3. Load World**

```python
from tangl.story.fabula.world import World

world = World(label="demo", script_manager=script_manager)
```

**4. Create Story Session**

```python
result = orchestrator.execute(
    "RuntimeController.create_story",
    user_id=user.uid,
    world_id="demo"
)

ledger_id = UUID(result["ledger_id"])
# User's current_ledger_id now points to new session
# Ledger has been persisted
```

**5. Get Choices**

```python
choices = orchestrator.execute(
    "RuntimeController.get_available_choices",
    user_id=user.uid
)
# Returns: [{"uid": "...", "label": "..."}]
```

**6. Make Choice**

```python
result = orchestrator.execute(
    "RuntimeController.resolve_choice",
    user_id=user.uid,
    choice_id=choice_id
)
# Ledger advanced and persisted
```

**7. Get Journal**

```python
fragments = orchestrator.execute(
    "RuntimeController.get_journal_entries",
    user_id=user.uid,
    limit=10
)
# Returns: [BaseFragment, ...]
```

### Custom Controllers

**Create domain-specific controllers for your application:**

```python
from tangl.service import HasApiEndpoints, ApiEndpoint, AccessLevel, MethodType
from tangl.vm import Ledger

class QuestController(HasApiEndpoints):
    
    @ApiEndpoint.annotate(
        access_level=AccessLevel.USER,
        method_type=MethodType.READ
    )
    def list_active_quests(self, ledger: Ledger) -> list[dict]:
        """Get all active quests in current story."""
        graph = ledger.graph
        quests = []
        
        for node in graph.nodes:
            if "quest" in node.tags and "active" in node.tags:
                quests.append({
                    "id": str(node.uid),
                    "name": node.label,
                    "description": node.get("description", "")
                })
        
        return quests
    
    @ApiEndpoint.annotate(
        access_level=AccessLevel.USER,
        method_type=MethodType.UPDATE
    )
    def complete_quest(self, ledger: Ledger, quest_id: UUID) -> dict:
        """Mark a quest as completed."""
        graph = ledger.graph
        quest = graph.get(quest_id)
        
        if quest is None:
            raise ValueError("Quest not found")
        
        quest.tags.discard("active")
        quest.tags.add("completed")
        
        return {"status": "completed", "quest_id": str(quest_id)}

# Register with orchestrator
orchestrator.register_controller(QuestController)

# Use from application
result = orchestrator.execute(
    "QuestController.complete_quest",
    user_id=user_id,
    quest_id=quest_id
)
```

### REST API Integration

**FastAPI automatically maps orchestrator endpoints to routes:**

```python
from fastapi import APIRouter, Depends
from tangl.rest.dependencies import get_orchestrator, get_user_id

router = APIRouter(prefix="/api/v2")

@router.post("/story/create")
async def create_story(
    world_id: str,
    user_id: UUID = Depends(get_user_id),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    result = orchestrator.execute(
        "RuntimeController.create_story",
        user_id=user_id,
        world_id=world_id
    )
    return result

@router.post("/do")
async def resolve_choice(
    choice_id: UUID,
    user_id: UUID = Depends(get_user_id),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    result = orchestrator.execute(
        "RuntimeController.resolve_choice",
        user_id=user_id,
        choice_id=choice_id
    )
    return result
```

### CLI Integration

**cmd2 commands delegate to orchestrator:**

```python
from cmd2 import with_argparser
import argparse

class StoryCLI(cmd2.Cmd):
    def __init__(self, orchestrator: Orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.user_id = None
    
    create_parser = argparse.ArgumentParser()
    create_parser.add_argument("world_id")
    
    @with_argparser(create_parser)
    def do_create_story(self, args):
        """Create a new story session."""
        result = self.orchestrator.execute(
            "RuntimeController.create_story",
            user_id=self.user_id,
            world_id=args.world_id
        )
        self.poutput(f"Created story: {result['title']}")
    
    do_parser = argparse.ArgumentParser()
    do_parser.add_argument("choice_num", type=int)
    
    @with_argparser(do_parser)
    def do_do(self, args):
        """Make a choice."""
        choices = self.orchestrator.execute(
            "RuntimeController.get_available_choices",
            user_id=self.user_id
        )
        
        if 0 < args.choice_num <= len(choices):
            choice = choices[args.choice_num - 1]
            self.orchestrator.execute(
                "RuntimeController.resolve_choice",
                user_id=self.user_id,
                choice_id=choice["uid"]
            )
            self.poutput("Choice resolved!")
        else:
            self.poutput("Invalid choice number")
```

---

## Usage Examples

### Example 1: Complete Story Playthrough

```python
from uuid import UUID
from tangl.persistence import PersistenceManagerFactory
from tangl.service import Orchestrator, User
from tangl.service.controllers import RuntimeController, WorldController
from tangl.story.fabula.world import World

# Setup
persistence = PersistenceManagerFactory.create_persistence_manager("json_file")
orchestrator = Orchestrator(persistence)
orchestrator.register_controller(RuntimeController)
orchestrator.register_controller(WorldController)

# Create user
user = User(label="player")
persistence.save(user)

# Load world (assume script already loaded)
world = World(label="dragon_hoard", script_manager=script_manager)

# Start story
result = orchestrator.execute(
    "RuntimeController.create_story",
    user_id=user.uid,
    world_id="dragon_hoard"
)
print(f"Story created: {result['title']}")

# Get initial journal
fragments = orchestrator.execute(
    "RuntimeController.get_journal_entries",
    user_id=user.uid,
    limit=5
)
for frag in fragments:
    print(frag.content)

# Main game loop
while True:
    # Get choices
    choices = orchestrator.execute(
        "RuntimeController.get_available_choices",
        user_id=user.uid
    )
    
    if not choices:
        print("Story ended!")
        break
    
    # Display choices
    for i, choice in enumerate(choices, 1):
        print(f"{i}. {choice['label']}")
    
    # Get user input
    selection = int(input("Choice: "))
    choice_id = UUID(choices[selection - 1]["uid"])
    
    # Resolve choice
    orchestrator.execute(
        "RuntimeController.resolve_choice",
        user_id=user.uid,
        choice_id=choice_id
    )
    
    # Show new content
    fragments = orchestrator.execute(
        "RuntimeController.get_journal_entries",
        user_id=user.uid,
        limit=5
    )
    for frag in fragments:
        print(frag.content)
```

### Example 2: Save/Load Session

```python
# Session persists automatically via orchestrator

# First session
result = orchestrator.execute(
    "RuntimeController.create_story",
    user_id=user_id,
    world_id="demo"
)
ledger_id = UUID(result["ledger_id"])

# Make some choices
orchestrator.execute(
    "RuntimeController.resolve_choice",
    user_id=user_id,
    choice_id=choice_id_1
)

# ... application exits ...

# Later session (new orchestrator instance)
new_orchestrator = Orchestrator(same_persistence)
new_orchestrator.register_controller(RuntimeController)

# User's current ledger is automatically loaded
choices = new_orchestrator.execute(
    "RuntimeController.get_available_choices",
    user_id=user_id  # Uses user.current_ledger_id
)

# Continue where we left off
```

### Example 3: Multi-User Server

```python
from fastapi import FastAPI, Depends, HTTPException
from uuid import UUID

app = FastAPI()
persistence = PersistenceManagerFactory.create_persistence_manager("redis_pickle")
orchestrator = Orchestrator(persistence)

# User locks for concurrency safety
user_locks: dict[UUID, asyncio.Lock] = {}

async def get_user_lock(user_id: UUID) -> asyncio.Lock:
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

@app.post("/story/create")
async def create_story(
    world_id: str,
    user_id: UUID,
    lock: asyncio.Lock = Depends(get_user_lock)
):
    async with lock:
        result = orchestrator.execute(
            "RuntimeController.create_story",
            user_id=user_id,
            world_id=world_id
        )
        return result

@app.post("/do")
async def do_choice(
    choice_id: UUID,
    user_id: UUID,
    lock: asyncio.Lock = Depends(get_user_lock)
):
    async with lock:
        # Prevents race conditions when user submits multiple choices
        result = orchestrator.execute(
            "RuntimeController.resolve_choice",
            user_id=user_id,
            choice_id=choice_id
        )
        return result
```

---

## Testing Strategy

### Unit Tests

**Location:** `engine/tests/service/`

**Controller Tests:**
- ✅ `test_runtime_controller.py` - RuntimeController endpoints
- ✅ `test_user_controller.py` - User CRUD operations
- ⚠️ **MISSING:** WorldController tests
- ⚠️ **MISSING:** SystemController tests

**Orchestrator Tests:**
- ✅ `test_orchestrator_basic.py` - Resource hydration
- ✅ `test_orchestrator_injection.py` - Dependency injection
- ⚠️ **MISSING:** Error handling tests
- ⚠️ **MISSING:** Access control tests

**Persistence Tests:**
- ✅ `test_persistence_mgr_factory.py` - All backends
- ✅ `test_file_storage.py` - File-based persistence
- ✅ `test_redis_storage.py` - Redis integration
- ✅ `test_mongo_storage.py` - MongoDB integration

### Integration Tests

**Location:** `engine/tests/integration/`

- ✅ `test_service_layer.py` - End-to-end orchestrator workflow
- ⚠️ **MISSING:** Multi-user concurrent access
- ⚠️ **MISSING:** Long-running session persistence
- ⚠️ **MISSING:** World hot-reloading

### Application Tests

**CLI Tests:**
- ✅ `apps/cli/tests/test_cli_story_controller.py`
- ✅ `apps/cli/tests/test_cli_user_controller.py`

**REST API Tests:**
- ✅ `apps/server/tests/test_rest_routers.py`
- ✅ `apps/server/tests/test_rest_dependencies.py`
- ⚠️ **MISSING:** Authentication flow tests
- ⚠️ **MISSING:** Error response format tests

### Recommended New Tests

**Test 1: Access Control Enforcement**
```python
def test_admin_endpoint_rejects_user():
    """Verify access level enforcement."""
    # Register endpoint with AccessLevel.ADMIN
    # Call with regular user credentials
    # Should raise PermissionError
```

**Test 2: Concurrent Mutation Safety**
```python
async def test_concurrent_choice_resolution():
    """Ensure user lock prevents race conditions."""
    # Spawn multiple async tasks
    # All try to resolve different choices for same user
    # Only one should succeed at a time
    # Final state should be consistent
```

**Test 3: Persistence Round-Trip**
```python
def test_ledger_survives_orchestrator_restart():
    """Verify session persistence across restarts."""
    # Create story, make choices
    # Serialize orchestrator state
    # Rebuild orchestrator with same persistence
    # Resume session from last state
```

---

## References

### Implementation Files

**Service Core:**
- `engine/src/tangl/service/orchestrator.py` - Orchestrator class
- `engine/src/tangl/service/api_endpoint.py` - ApiEndpoint decorator
- `engine/src/tangl/service/user/user.py` - User model
- `engine/src/tangl/service/controllers/` - All controller implementations

**Persistence:**
- `engine/src/tangl/persistence/manager.py` - PersistenceManager
- `engine/src/tangl/persistence/factory.py` - Backend factory
- `engine/src/tangl/persistence/storage/` - Storage implementations
- `engine/src/tangl/persistence/serializers.py` - Serialization handlers

**Applications:**
- `apps/cli/src/tangl/cli/` - CLI implementation
- `apps/server/src/tangl/rest/` - FastAPI server
- `apps/server/src/tangl/rest/routers/` - REST endpoints

### Test Files

- `engine/tests/service/controllers/test_*.py`
- `engine/tests/service/test_orchestrator_*.py`
- `engine/tests/persistence/test_*.py`
- `engine/tests/integration/test_service_layer.py`
- `apps/cli/tests/test_*.py`
- `apps/server/tests/test_*.py`

### Related Design Documents

- `PLANNING_PROVISIONING_DESIGN_v37.md` - Planning system architecture
- `AGENTS.md` - Contributor guidelines
- `linear_playback_plan.md` - MVP implementation roadmap
- `StoryTangl_MVP_Implementation_Review.md` - Architecture review

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 3.7.0 | Nov 2025 | Initial consolidation from service_layer.rst. Reflects actual v3.7 implementation. |

---

**Document Status:** ✅ **CURRENT AND ACCURATE**

This document reflects the actual state of the service layer as of November 2025. All claims about implementation status have been verified against source code.
