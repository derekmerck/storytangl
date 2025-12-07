# Media Subsystem Design (v3.7)

**Status:** This document reflects the **target architecture** for media integration with v3.7.  
**Last Updated:** November 2025  
**Location:** `engine/src/tangl/media/` and `engine/src/tangl/journal/media/`

---

## Executive Summary

StoryTangl's media subsystem enables **rich multimedia narratives** by:
- ✅ Abstracting media resources through **MediaResourceInventoryTag (MediaRIT)** indirection
- ✅ Integrating with **VM provisioning** to resolve media dependencies during planning
- ✅ Supporting **multiple media sources**: direct paths, in-memory data, generative specs
- ✅ Deferring **client-specific resolution** to the service layer (URLs vs inline data)
- ✅ Enabling **extensible creator pipelines** (generative AI, SVG paperdolls, TTS, etc.)

**Key Insight:** Media follows the same lifecycle as other resources—dependencies declared in scripts, provisioned during PLANNING phase, emitted as fragments during JOURNAL phase, and dereferenced by service layer for client delivery. The MediaRIT abstraction decouples narrative structure from storage/delivery mechanics.

---

## Core Concepts

### MediaResourceInventoryTag (MediaRIT)

**The MediaRIT is an indirection layer that decouples narrative references from actual media storage.**

```python
# Three construction patterns:

# 1. Direct path reference (simplest)
rit_path = MediaRIT(
    path="assets/images/dragon.png",
    media_type=MediaDataType.IMAGE
)

# 2. In-memory data
rit_data = MediaRIT(
    data=image_bytes,
    media_type=MediaDataType.IMAGE,
    content_hash=hash_bytes(image_bytes)
)

# 3. Deferred spec (created on-demand)
rit_spec = MediaRIT(
    spec=StableDiffusionSpec(
        prompt="majestic dragon in a treasure hoard",
        style="fantasy_art"
    ),
    media_type=MediaDataType.IMAGE
)
```

**What a MediaRIT provides:**
- **Unique identifier** (`uid`) for registry lookup and deduplication
- **Content hash** for content-addressed caching
- **Metadata** (media type, mime type, dimensions, staging hints)
- **Source information** (path, data, or spec for creation)
- **Lifecycle tracking** (creation time, availability status)

**What a MediaRIT does NOT contain:**
- Client-relative URLs (determined by service layer)
- Transport format decisions (Base64 inline vs URL reference)
- Application-specific rendering hints (those go in MediaFragment)

### Media Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Script Layer                             │
│  (Author's intent)                                          │
│                                                             │
│  MediaScriptItem:                                           │
│    - media_id: "dragon_image"                               │
│    - media_path: "assets/dragon.png"                        │
│    - media_spec: {...generative spec...}                    │
│    - media_data: <bytes>                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  Dependency Layer                           │
│  (Graph structure)                                          │
│                                                             │
│  MediaDependency edge:                                      │
│    source: Block/Concept                                    │
│    destination: None (to be resolved)                       │
│    requirement: MediaRequirement(...)                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                 Provisioning Layer (VM)                     │
│  (Resource resolution)                                      │
│                                                             │
│  MediaProvisioner:                                          │
│    1. Check MediaResourceRegistry for existing RIT         │
│    2. If not found, create via:                             │
│       - Direct path attachment                              │
│       - Spec adaptation → MediaForge → new RIT              │
│    3. Bind RIT to dependency edge                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   Fragment Layer (Journal)                  │
│  (Rendering output)                                         │
│                                                             │
│  MediaFragment:                                             │
│    content: MediaRIT                                        │
│    content_format: "rit"                                    │
│    media_role: "narrative_im"                               │
│    staging_hints: orientation, placement, etc.              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                Service Layer (Dereferencing)                │
│  (Client delivery)                                          │
│                                                             │
│  Dereference MediaRIT to:                                   │
│    - URL: https://api/media/dragon_abc123.png               │
│    - Data: {"data": "base64...", "mime": "image/png"}      │
│    - Path: (for desktop/CLI clients)                       │
└─────────────────────────────────────────────────────────────┘
```

### Media Roles

**Media roles hint at narrative intent, not technical format.**

Common roles:
- `narrative_im` - Scene-setting image (landscapes, portraits)
- `dialog_vo` - Character voice-over for dialog
- `ambient_music` - Background music for scenes
- `sound_fx` - Action sound effects
- `ui_icon` - Interface element (item icons, status badges)
- `anim_sprite` - Animated character sprites
- `video_cutscene` - Cinematic sequence

Roles inform:
- **Client rendering decisions** (full-bleed vs inline, audio ducking, etc.)
- **Staging hints** (orientation, layering, looping behavior)
- **Resource prioritization** (preload narrative images, lazy-load icons)

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Story Layer                            │
│  (tangl.story.fabula, tangl.story.episode)                 │
│                                                             │
│  • Compiles MediaScriptItem → MediaDependency edges         │
│  • Blocks/Concepts emit MediaFragment during JOURNAL        │
│  • ContentRenderer handles media template expansion         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    VM Provision Layer                       │
│  (tangl.vm.provision, tangl.vm.dispatch.planning)          │
│                                                             │
│  MediaProvisioner:                                          │
│    • Discovers existing RIT via MediaResourceRegistry       │
│    • Creates new RIT via MediaForge dispatch                │
│    • Binds RIT to MediaDependency edges                     │
│                                                             │
│  Integration: Runs during PLANNING phase (P.PLANNING)       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   Media Resource Layer                      │
│  (tangl.media.media_resource)                              │
│                                                             │
│  • MediaResourceInventoryTag (Entity)                       │
│  • MediaResourceRegistry (Registry)                         │
│  • MediaRequirement (Requirement[MediaRIT])                 │
│  • MediaProvisioner (Provisioner)                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  Media Creator Layer                        │
│  (tangl.media.media_creators)                              │
│                                                             │
│  MediaForge dispatch:                                       │
│    • on_adapt_media_spec: Context-aware spec refinement     │
│    • on_create_media: Actual media generation               │
│                                                             │
│  Implementations:                                           │
│    • StableForge (Stable Diffusion API)                     │
│    • SvgPaperdollForge (SVG composition)                    │
│    • TtsForge (text-to-speech)                              │
│    • (extensible...)                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    Journal Layer                            │
│  (tangl.journal.media)                                     │
│                                                             │
│  • MediaFragment (ContentFragment subclass)                 │
│  • Emitted during JOURNAL phase by story nodes              │
│  • Contains MediaRIT reference + staging hints              │
│  • Service layer resolves RIT → client format               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                 Service/Controller Layer                    │
│  (tangl.service.controllers)                               │
│                                                             │
│  Dereference pipeline:                                      │
│    1. Collect MediaFragments from journal                   │
│    2. Extract MediaRIT from each fragment                   │
│    3. Resolve RIT to client-appropriate format:             │
│       - Web: Generate signed URL                            │
│       - Mobile: Base64 inline for small assets              │
│       - Desktop: Absolute file path                         │
│    4. Attach mime type, dimensions, etc.                    │
└─────────────────────────────────────────────────────────────┘
```

---

## The Media Lifecycle

### 1. Script Declaration

**Authors declare media in story scripts using MediaScriptItem.**

```yaml
# YAML script example
blocks:
  - id: dragon_lair
    content: |
      You enter the dragon's lair. Gold coins glitter in the firelight.
    
    media:
      - media_id: "lair_background"
        media_path: "assets/images/dragon_lair.png"
        media_role: "narrative_im"
        staging_hints:
          orientation: "landscape"
          placement: "background"
      
      - media_id: "dragon_roar"
        media_spec:
          type: "stable_diffusion"
          prompt: "fierce red dragon breathing fire"
          style: "photorealistic"
        media_role: "narrative_im"
        staging_hints:
          orientation: "portrait"
```

**Script compilation:** `MediaScriptItem` → `MediaDependency` edge

```python
# During World.create_story():
for media_item in block_script.media:
    requirement = MediaRequirement(
        graph=story,
        identifier=media_item.media_id,
        policy=ProvisioningPolicy.ANY,
        template=media_item.model_dump(),  # Full script data
        hard_requirement=False  # Media is usually soft requirement
    )
    
    dep = MediaDependency(
        graph=story,
        source_id=block.uid,
        requirement=requirement,
        label=media_item.media_id
    )
```

### 2. Provisioning (PLANNING Phase)

**During frame.run_phase(P.PLANNING), MediaProvisioner resolves dependencies.**

```python
# Simplified provisioning flow:

class MediaProvisioner(Provisioner[MediaRIT]):
    """Discover or create MediaRIT for media dependencies."""
    
    def _resolve_existing(
        self, 
        requirement: MediaRequirement
    ) -> MediaRIT | None:
        """Search MediaResourceRegistry by identifier or hash."""
        registry = self.get_media_registry()
        
        # Try by identifier first
        if requirement.identifier:
            rit = registry.find(uid=requirement.identifier)
            if rit and rit.is_available():
                return rit
        
        # Try by content hash (deduplication)
        if requirement.template.get('media_path'):
            path = requirement.template['media_path']
            content_hash = hash_file(path)
            rit = registry.find_by_hash(content_hash)
            if rit:
                return rit
        
        return None
    
    def _resolve_create(
        self,
        requirement: MediaRequirement
    ) -> MediaRIT:
        """Create new MediaRIT from path, data, or spec."""
        template = requirement.template
        
        # Path → direct attachment
        if 'media_path' in template:
            return self._attach_from_path(template)
        
        # Data → in-memory RIT
        if 'media_data' in template:
            return self._attach_from_data(template)
        
        # Spec → forge creation
        if 'media_spec' in template:
            return self._create_from_spec(template, requirement)
        
        raise ValueError("MediaRequirement needs path, data, or spec")
    
    def _create_from_spec(
        self,
        template: dict,
        requirement: MediaRequirement
    ) -> MediaRIT:
        """Invoke MediaForge pipeline to generate media."""
        spec = MediaSpec.from_dict(template['media_spec'])
        
        # 1. Adapt spec to context (optional refinement)
        adapted_spec = self._adapt_spec(spec, requirement.reference)
        
        # 2. Check if adapted spec already exists
        registry = self.get_media_registry()
        existing = registry.find_by_spec_hash(adapted_spec.spec_hash)
        if existing:
            return existing
        
        # 3. Create media via forge
        media_bytes, final_spec = self._invoke_forge(adapted_spec)
        
        # 4. Wrap in RIT and register
        rit = MediaRIT(
            data=media_bytes,
            spec=adapted_spec,
            final_spec=final_spec,
            media_type=self._infer_media_type(final_spec),
            content_hash=hash_bytes(media_bytes)
        )
        
        registry.add(rit)
        return rit
```

**Provisioning order (priority-based):**

```python
# In planning.py handlers:

@vm_dispatch.register(task=P.PLANNING, priority=Prio.EARLY)
def index_requirements(*, frame: Frame, **_):
    """Collect all open edges (including MediaDependency)."""
    # ... existing logic ...

@vm_dispatch.register(task=P.PLANNING, priority=Prio.NORMAL)
def gather_offers(*, frame: Frame, **_):
    """Invoke provisioners to generate offers."""
    # MediaProvisioner runs here alongside RoleProvisioner, etc.
    # ... existing logic ...

@vm_dispatch.register(task=P.PLANNING, priority=Prio.LATE)
def apply_offers(*, frame: Frame, **_):
    """Accept offers, bind resources to edges."""
    # MediaDependency edges get destination_id = rit.uid
    # ... existing logic ...
```

### 3. Fragment Emission (JOURNAL Phase)

**Blocks/Concepts emit MediaFragment during rendering.**

```python
class Concept(Node):
    """Concept with optional media attachment."""
    
    def get_media_dependency(self) -> MediaDependency | None:
        """Find bound media dependency edge."""
        for edge in self.edges_out(is_instance=MediaDependency):
            if edge.destination_id:  # Provisioned
                return edge
        return None
    
    def concept_fragment(self, *, ctx: Context) -> BaseFragment:
        """Generate concept fragment with optional media."""
        media_fragment = None
        
        # Check for provisioned media
        media_dep = self.get_media_dependency()
        if media_dep:
            rit = media_dep.destination  # type: MediaRIT
            media_fragment = MediaFragment(
                content=rit,
                content_format="rit",
                content_type=rit.media_type,
                media_role="concept_image",
                staging_hints=StagingHints(
                    orientation="square",
                    placement="inline"
                ),
                source_id=self.uid,
                source_label=self.label
            )
        
        # Main concept fragment
        return BaseFragment(
            content=self.render_content(ctx),
            source_id=self.uid,
            fragment_type="concept",
            media_fragment=media_fragment  # Nested or separate?
        )
```

**Fragment structure:**

```python
MediaFragment(
    # Core ContentFragment fields
    fragment_type="media",
    source_id="concept_dragon_uid",
    source_label="dragon",
    
    # Media-specific fields
    content=MediaRIT(...),  # CRITICAL: RIT, not resolved data
    content_format="rit",
    content_type=MediaDataType.IMAGE,
    
    # Rendering hints
    media_role="narrative_im",
    staging_hints=StagingHints(
        orientation="landscape",
        placement="background",
        z_index=0
    )
)
```

### 4. Service Layer Dereferencing

**RuntimeController resolves MediaRIT → client format during response building.**

```python
class RuntimeController:
    """Service controller for story runtime operations."""
    
    def get_state(
        self,
        *,
        ledger: Ledger,
        frame: Frame,
        user: User,
        **_
    ) -> dict:
        """
        GET /state endpoint.
        
        Returns current story state with dereferenced media.
        """
        # 1. Collect journal fragments
        fragments = list(ledger.get_journal(since='current_step'))
        
        # 2. Dereference media fragments
        dereferenced = []
        for frag in fragments:
            if isinstance(frag, MediaFragment):
                dereferenced.append(
                    self._dereference_media_fragment(frag, user)
                )
            else:
                dereferenced.append(frag)
        
        return {
            'fragments': dereferenced,
            'choices': self._get_choices(frame),
            'cursor': frame.cursor.uid
        }
    
    def _dereference_media_fragment(
        self,
        fragment: MediaFragment,
        user: User
    ) -> dict:
        """
        Resolve MediaRIT to client-appropriate format.
        
        Returns dict suitable for JSON serialization.
        """
        rit = fragment.content  # type: MediaRIT
        
        # Determine client type from user session/headers
        client_type = user.client_preference  # 'web', 'mobile', 'desktop'
        
        if client_type == 'web':
            # Generate signed URL
            url = self._generate_media_url(rit, user)
            return {
                'fragment_type': 'media',
                'media_role': fragment.media_role,
                'url': url,
                'mime_type': rit.mime_type,
                'staging_hints': fragment.staging_hints.model_dump(),
                'source_id': fragment.source_id
            }
        
        elif client_type == 'mobile':
            # Inline Base64 for small assets, URL for large
            if rit.size_bytes < 100_000:  # < 100KB
                data_b64 = self._encode_media_data(rit)
                return {
                    'fragment_type': 'media',
                    'media_role': fragment.media_role,
                    'data': data_b64,
                    'mime_type': rit.mime_type,
                    'staging_hints': fragment.staging_hints.model_dump()
                }
            else:
                url = self._generate_media_url(rit, user)
                return {
                    'fragment_type': 'media',
                    'media_role': fragment.media_role,
                    'url': url,
                    'mime_type': rit.mime_type,
                    'staging_hints': fragment.staging_hints.model_dump()
                }
        
        elif client_type == 'desktop':
            # Absolute file path
            abs_path = self._resolve_media_path(rit)
            return {
                'fragment_type': 'media',
                'media_role': fragment.media_role,
                'path': str(abs_path),
                'mime_type': rit.mime_type,
                'staging_hints': fragment.staging_hints.model_dump()
            }
    
    def _generate_media_url(self, rit: MediaRIT, user: User) -> str:
        """Generate client-relative URL for media resource."""
        # Example: https://api.example.com/media/{content_hash}.{ext}
        base_url = self.config.media_base_url
        ext = mime_to_extension(rit.mime_type)
        
        # URL includes content hash for cache busting + CDN
        return f"{base_url}/{rit.content_hash[:16]}.{ext}"
    
    def _encode_media_data(self, rit: MediaRIT) -> str:
        """Load media bytes and Base64 encode."""
        media_bytes = self._load_media_bytes(rit)
        return base64.b64encode(media_bytes).decode('utf-8')
    
    def _resolve_media_path(self, rit: MediaRIT) -> Path:
        """Resolve RIT to absolute filesystem path."""
        if rit.path:
            return Path(rit.path).resolve()
        
        # Fall back to content-addressed cache
        cache_dir = self.config.media_cache_dir
        ext = mime_to_extension(rit.mime_type)
        return cache_dir / f"{rit.content_hash}.{ext}"
```

**Dereferencing strategies:**

| Client Type | Small Assets (<100KB) | Large Assets (>100KB) |
|-------------|----------------------|----------------------|
| Web         | Signed URL           | Signed URL           |
| Mobile      | Base64 inline        | Signed URL           |
| Desktop/CLI | Absolute path        | Absolute path        |

---

## Provisioning Integration

### MediaRequirement Specification

**MediaRequirement extends Requirement[MediaRIT] with media-specific fields.**

```python
@dataclass
class MediaRequirement(Requirement[MediaRIT]):
    """
    Requirement for media resources.
    
    Supports three resolution patterns:
    1. identifier → existing RIT lookup
    2. media_path → path attachment
    3. media_spec → forge creation
    """
    
    # Standard Requirement fields
    graph: Graph
    identifier: str | None = None
    criteria: dict = field(default_factory=dict)
    template: dict = field(default_factory=dict)
    policy: ProvisioningPolicy = ProvisioningPolicy.ANY
    hard_requirement: bool = False
    
    # Media-specific fields
    media_id: str | None = None
    media_path: Pathlike | None = None
    media_spec: MediaSpec | None = None
    media_role: str | None = None
    
    def __post_init__(self):
        """Extract media fields from template if present."""
        if self.template:
            self.media_id = self.template.get('media_id')
            self.media_path = self.template.get('media_path')
            self.media_role = self.template.get('media_role')
            
            if 'media_spec' in self.template:
                self.media_spec = MediaSpec.from_dict(
                    self.template['media_spec']
                )
```

### MediaDependency Edge

**MediaDependency is a DependencyEdge specialized for media provisioning.**

```python
class MediaDependency(DependencyEdge):
    """
    Dependency edge for media resources.
    
    Pattern: Block/Concept → (dependency) → MediaRIT
    
    Flow:
    1. Created during script compilation with open destination
    2. Resolved during PLANNING phase by MediaProvisioner
    3. destination_id set to provisioned MediaRIT.uid
    4. Referenced during JOURNAL phase to emit MediaFragment
    """
    
    requirement: MediaRequirement
    
    def is_satisfied(self) -> bool:
        """Check if media dependency has been provisioned."""
        return self.destination_id is not None
    
    def get_media_rit(self) -> MediaRIT | None:
        """Retrieve provisioned MediaRIT."""
        if self.destination_id:
            return self.destination  # type: MediaRIT
        return None
```

### Provisioning Priority

**Media provisioning runs at NORMAL priority during PLANNING phase.**

```
PLANNING Phase Execution Order:
-----------------------------
1. EARLY (10):   Index all open edges (Dependencies, Affordances)
2. NORMAL (50):  Generate offers from provisioners
                 • RoleProvisioner (actors)
                 • ItemProvisioner (items)
                 • MediaProvisioner (media) ← HERE
3. LATE (90):    Apply best offers, bind resources
4. LAST (100):   Summarize provisioning receipt
```

**Why NORMAL priority?**
- Media is typically a **soft requirement** (story continues without it)
- Allows character/item provisioning to complete first
- Prevents expensive forge operations from blocking hard requirements
- Can be overridden per-dependency with `hard_requirement=True`

---

## Fragment Rendering & Dereferencing

### Fragment Emission Pattern

**Blocks emit MediaFragment during JOURNAL phase, similar to concept fragments.**

```python
# Example: Block with background image

class Block(Node):
    """Block with multi-handler JOURNAL pattern."""
    
    @story_dispatch.register(task=P.JOURNAL, priority=Prio.EARLY)
    def block_fragment(self, *, ctx: Context, **_) -> BaseFragment:
        """Render block prose content."""
        return BaseFragment(
            content=self.render_content(ctx),
            fragment_type="block",
            source_id=self.uid
        )
    
    @story_dispatch.register(task=P.JOURNAL, priority=Prio.NORMAL)
    def media_fragments(self, *, ctx: Context, **_) -> list[MediaFragment]:
        """Emit media fragments for bound media dependencies."""
        fragments = []
        
        for edge in self.edges_out(is_instance=MediaDependency):
            if not edge.is_satisfied():
                continue  # Skip unprovisioned (soft requirement)
            
            rit = edge.get_media_rit()
            media_item = edge.requirement.template  # Original script
            
            fragment = MediaFragment(
                content=rit,
                content_format="rit",
                content_type=rit.media_type,
                media_role=media_item.get('media_role', 'media'),
                staging_hints=StagingHints(
                    **media_item.get('staging_hints', {})
                ),
                source_id=self.uid,
                source_label=self.label
            )
            fragments.append(fragment)
        
        return fragments or None
```

**Fragment order:**
```
Block JOURNAL execution:
1. EARLY:  block_fragment() → BaseFragment (prose)
2. NORMAL: media_fragments() → list[MediaFragment]
3. NORMAL: describe_concepts() → list[BaseFragment] (concept prose)
4. LATE:   provide_choices() → list[ChoiceFragment]

Result: Interleaved prose, media, concepts, choices
```

### Service Layer Resolution

**The service layer is the ONLY place where MediaRIT → client data happens.**

```python
# ❌ NEVER do this in story/VM code:
media_url = f"https://api.example.com/media/{rit.uid}.png"
fragment = MediaFragment(content=media_url, ...)  # WRONG

# ✅ ALWAYS emit MediaRIT in fragments:
fragment = MediaFragment(content=rit, content_format="rit", ...)
# Service layer resolves RIT later based on client needs
```

**Why defer dereferencing?**
- **Client independence**: Web vs mobile vs desktop have different needs
- **Security**: Signed URLs, authentication, rate limiting
- **Caching**: CDN integration, content-addressed storage
- **Flexibility**: Inline vs URL decision based on size/network
- **Testing**: Mock media resolution without touching storage

---

## Creator Pipeline

### MediaSpec Abstraction

**MediaSpec defines the interface between requirements and forges.**

```python
class MediaSpec(BaseModelPlus):
    """
    Base class for media creation specifications.
    
    Subclasses define forge-specific parameters.
    """
    
    # Common fields
    media_type: MediaDataType
    spec_type: str  # "stable_diffusion", "svg_paperdoll", "tts"
    
    # Metadata
    spec_hash: str = ""  # Content-addressed cache key
    
    def __post_init__(self):
        """Compute spec hash for deduplication."""
        self.spec_hash = self.compute_hash()
    
    def compute_hash(self) -> str:
        """Generate content-based hash of spec parameters."""
        spec_dict = self.model_dump(exclude={'spec_hash'})
        return hash_dict(spec_dict)
    
    # Dispatch hooks
    @classmethod
    def adapt_spec(cls, spec: MediaSpec, context_node: Node) -> MediaSpec:
        """
        Adapt spec based on narrative context.
        
        Example: Inject character appearance details from actor node.
        """
        # Dispatch to on_adapt_media_spec registry
        results = on_adapt_media_spec.dispatch(
            spec=spec,
            context=context_node
        )
        return results[0] if results else spec
    
    @classmethod
    def create_media(cls, spec: MediaSpec) -> tuple[bytes, MediaSpec]:
        """
        Generate media from spec.
        
        Returns: (media_bytes, realized_spec)
        """
        # Dispatch to on_create_media registry
        results = on_create_media.dispatch(spec=spec)
        if not results:
            raise ValueError(f"No forge registered for {spec.spec_type}")
        return results[0]


# Dispatch registries
on_adapt_media_spec = BehaviorRegistry(
    label="adapt_media_spec",
    aggregation_strategy="replace"  # Last adapter wins
)

on_create_media = BehaviorRegistry(
    label="create_media",
    aggregation_strategy="replace"  # Last creator wins
)
```

### Example Spec: Stable Diffusion

```python
class StableDiffusionSpec(MediaSpec):
    """Spec for Stable Diffusion image generation."""
    
    spec_type: Literal["stable_diffusion"] = "stable_diffusion"
    media_type: MediaDataType = MediaDataType.IMAGE
    
    # Generation parameters
    prompt: str
    negative_prompt: str = ""
    style: str = "default"
    width: int = 512
    height: int = 512
    steps: int = 20
    guidance_scale: float = 7.5
    seed: int | None = None
    
    # Model selection
    model_id: str = "stabilityai/stable-diffusion-2-1"


# Adapter: Inject character details
@on_adapt_media_spec.register(priority=Prio.NORMAL)
def adapt_character_image_spec(
    *,
    spec: MediaSpec,
    context: Node,
    **_
) -> MediaSpec | None:
    """
    Enhance image prompts with character appearance.
    
    Example:
      Original: "portrait of warrior"
      Adapted: "portrait of tall female warrior with red hair and scar"
    """
    if not isinstance(spec, StableDiffusionSpec):
        return None  # Skip non-SD specs
    
    if not isinstance(context, Character):
        return None  # Not a character context
    
    # Inject appearance details
    appearance = context.get_attribute('appearance', {})
    enhanced_prompt = f"{spec.prompt}, {appearance.get('description', '')}"
    
    return StableDiffusionSpec(
        **spec.model_dump(),
        prompt=enhanced_prompt
    )


# Creator: Invoke Stable Diffusion API
@on_create_media.register(priority=Prio.NORMAL)
def create_stable_diffusion_image(
    *,
    spec: MediaSpec,
    **_
) -> tuple[bytes, MediaSpec] | None:
    """Generate image via Stable Diffusion API."""
    if not isinstance(spec, StableDiffusionSpec):
        return None
    
    # Invoke external API
    api_client = StableDiffusionClient(api_key=config.sd_api_key)
    
    result = api_client.generate(
        prompt=spec.prompt,
        negative_prompt=spec.negative_prompt,
        width=spec.width,
        height=spec.height,
        steps=spec.steps,
        guidance_scale=spec.guidance_scale,
        seed=spec.seed or random.randint(0, 2**32)
    )
    
    # Return bytes + realized spec (with actual seed used)
    realized_spec = StableDiffusionSpec(
        **spec.model_dump(),
        seed=result.seed  # Record actual seed for reproducibility
    )
    
    return result.image_bytes, realized_spec
```

### Forge Extensibility

**Adding new forges is straightforward:**

```python
# 1. Define spec subclass
class SvgPaperdollSpec(MediaSpec):
    spec_type: Literal["svg_paperdoll"] = "svg_paperdoll"
    media_type: MediaDataType = MediaDataType.VECTOR
    
    body_type: str
    outfit: str
    accessories: list[str] = []

# 2. Register creator
@on_create_media.register(priority=Prio.NORMAL)
def create_svg_paperdoll(*, spec: MediaSpec, **_):
    if not isinstance(spec, SvgPaperdollSpec):
        return None
    
    svg_template = load_template(spec.body_type)
    svg_rendered = apply_layers(svg_template, spec.outfit, spec.accessories)
    svg_bytes = svg_rendered.encode('utf-8')
    
    return svg_bytes, spec

# 3. Use in scripts
media:
  - media_spec:
      type: "svg_paperdoll"
      body_type: "female_athletic"
      outfit: "leather_armor"
      accessories: ["sword", "shield"]
```

---

## What's Implemented

### ✅ Core Infrastructure (Stable)

**MediaRIT Entity:**
- [x] `MediaResourceInventoryTag` with uid, content_hash, metadata
- [x] Path-based, data-based, spec-based construction
- [x] Entity integration (persistent, serializable)

**Registry:**
- [x] `MediaResourceRegistry` with add/find operations
- [x] Content-addressed deduplication via hash lookup
- [x] Registry integration (indexing, scoped search)

**Fragment:**
- [x] `MediaFragment` with MediaRIT content
- [x] Staging hints (orientation, placement, z-index)
- [x] Media role field for client interpretation
- [x] Base64 serialization for binary content

### ⚠️ Partial Implementation (Needs Modernization)

**Provisioning:**
- [x] `MediaDependency` edge structure
- [x] `MediaProvisioner` basic skeleton
- [ ] **TODO:** Align with v3.7 Provisioner base class
- [ ] **TODO:** Implement offer generation (EXISTING/CREATE)
- [ ] **TODO:** Wire into planning.py handlers

**Scripts:**
- [x] `MediaScriptItem` schema (basic)
- [ ] **TODO:** Full YAML integration with ScriptManager
- [ ] **TODO:** Media role and staging hint validation

**Spec System:**
- [x] `MediaSpec` base class and dispatch registries
- [x] `StableForge` proof-of-concept (bespoke API)
- [ ] **TODO:** Standardize creator handler signatures
- [ ] **TODO:** Document adapter vs creator patterns

---

## What's Missing

### 🔴 Critical Gaps

1. **MediaRequirement Implementation**
   - Need: `MediaRequirement(Requirement[MediaRIT])` subclass
   - Purpose: Type-safe requirement for media provisioning
   - Integration: Used by MediaProvisioner, validated by planning phase

2. **Provisioner Integration**
   - Need: Wire MediaProvisioner into planning.py handlers
   - Current: Provisioner exists but not invoked during PLANNING
   - Impact: Media dependencies never resolved, fragments empty

3. **Service Layer Dereferencing**
   - Need: RuntimeController media resolution logic
   - Current: MediaFragment emitted with RIT, never dereferenced
   - Impact: Clients receive opaque RIT objects instead of URLs/data

4. **MediaDep → Fragment Wiring**
   - Need: Block/Concept JOURNAL handlers emit MediaFragment
   - Current: Concepts have `concept_fragment()` but no media logic
   - Impact: Provisioned media never appears in output

### 🟡 Important Enhancements

5. **Creator Pipeline Documentation**
   - Need: Clear adapter/creator handler patterns
   - Current: `on_adapt_media_spec` and `on_create_media` exist but unused
   - Impact: Hard to add new forge types

6. **Spec Validation**
   - Need: Pydantic validators for spec parameters
   - Current: Loose dict-based specs
   - Impact: Runtime errors instead of compile-time

7. **Media Registry Indexing**
   - Need: `on_index` dispatch for MediaRIT
   - Current: Basic add/find operations only
   - Impact: No audit trail for media creation

8. **Comprehensive Testing**
   - Need: Tests for provisioning, fragment emission, dereferencing
   - Current: Only basic fragment serialization tests
   - Impact: Unclear if integration works end-to-end

---

## Integration Points

### With VM Provisioning

**Entry point: `planning.py` NORMAL priority handler**

```python
@vm_dispatch.register(task=P.PLANNING, priority=Prio.NORMAL)
def gather_offers(*, frame: Frame, **_):
    """Generate offers from all provisioners."""
    
    # Collect all open edges (including MediaDependency)
    open_edges = ctx.get_open_edges()
    
    for edge in open_edges:
        if isinstance(edge, MediaDependency):
            # Invoke MediaProvisioner
            provisioner = MediaProvisioner(
                requirement=edge.requirement,
                registries=[ctx.media_registry],
                frame=frame
            )
            
            offers = provisioner.generate_offers()
            for offer in offers:
                ctx.planning_state.add_offer(offer)
```

### With Block Rendering

**Entry point: Block JOURNAL handlers**

```python
class Block(Node):
    @story_dispatch.register(task=P.JOURNAL, priority=Prio.NORMAL)
    def media_fragments(self, *, ctx: Context, **_):
        """Emit media fragments for provisioned media."""
        fragments = []
        
        for dep in self.edges_out(is_instance=MediaDependency):
            if dep.is_satisfied():
                rit = dep.destination  # MediaRIT
                fragments.append(MediaFragment(
                    content=rit,
                    content_format="rit",
                    media_role=dep.requirement.media_role,
                    # ... staging hints ...
                ))
        
        return fragments or None
```

### With Service Layer

**Entry point: RuntimeController response formatting**

```python
class RuntimeController:
    def get_state(self, *, ledger: Ledger, user: User, **_):
        """GET /state with dereferenced media."""
        fragments = ledger.get_journal('current_step')
        
        # Dereference media fragments
        response_fragments = []
        for frag in fragments:
            if isinstance(frag, MediaFragment):
                dereferenced = self._dereference_media(frag, user)
                response_fragments.append(dereferenced)
            else:
                response_fragments.append(frag.model_dump())
        
        return {'fragments': response_fragments, ...}
```

---

## Usage Examples

### Example 1: Simple Image Attachment

```python
# Story script (YAML)
blocks:
  - id: tavern
    content: "You enter the smoky tavern."
    media:
      - media_id: "tavern_bg"
        media_path: "assets/images/tavern.png"
        media_role: "narrative_im"
        staging_hints:
          orientation: "landscape"
          placement: "background"

# Result flow:
# 1. Script compilation → MediaDependency edge
# 2. PLANNING phase → MediaProvisioner attaches existing file
# 3. JOURNAL phase → Block emits MediaFragment(content=MediaRIT(...))
# 4. Service layer → Resolves to URL: https://api/media/abc123.png
```

### Example 2: Generated Character Portrait

```python
# Story script
concepts:
  - id: warrior_npc
    type: "character"
    content: "A battle-scarred warrior."
    attributes:
      appearance:
        description: "tall, muscular, red hair, facial scar"
    media:
      - media_id: "warrior_portrait"
        media_spec:
          type: "stable_diffusion"
          prompt: "portrait of warrior"
          style: "fantasy_art"
          width: 512
          height: 768
        media_role: "concept_image"
        staging_hints:
          orientation: "portrait"
          placement: "inline"

# Flow:
# 1. MediaDependency with StableDiffusionSpec
# 2. PLANNING → MediaProvisioner:
#    a) Adapt spec: inject appearance details
#    b) Check cache: spec_hash lookup
#    c) If miss: invoke StableForge → generate image
#    d) Wrap bytes in MediaRIT, register
# 3. JOURNAL → Concept emits MediaFragment
# 4. Service layer → URL or Base64 depending on client
```

### Example 3: SVG Paperdoll

```python
# Story script
concepts:
  - id: player_avatar
    type: "character"
    media:
      - media_id: "avatar_sprite"
        media_spec:
          type: "svg_paperdoll"
          body_type: "female_athletic"
          outfit: "leather_armor"
          accessories: ["sword", "shield", "health_potion"]
        media_role: "ui_icon"
        staging_hints:
          placement: "hud"
          z_index: 100

# Flow:
# 1. MediaDependency with SvgPaperdollSpec
# 2. PLANNING → SvgForge composes SVG layers
# 3. JOURNAL → Character emits MediaFragment
# 4. Service layer → Inline SVG (small size)
```

### Example 4: Multi-Media Scene

```python
# Complex scene with background, character, and sound
blocks:
  - id: dragon_lair_entrance
    content: |
      You stand before the dragon's lair. Heat radiates from the cave mouth.
      In the shadows, you glimpse the glint of scales.
    
    media:
      # Background image
      - media_id: "lair_exterior"
        media_path: "assets/images/dragon_lair.png"
        media_role: "narrative_im"
        staging_hints:
          orientation: "landscape"
          placement: "background"
          z_index: 0
      
      # Generated dragon portrait
      - media_id: "dragon_glimpse"
        media_spec:
          type: "stable_diffusion"
          prompt: "red dragon in shadows, glowing eyes"
          style: "dark_fantasy"
          width: 512
          height: 512
        media_role: "narrative_im"
        staging_hints:
          orientation: "square"
          placement: "foreground"
          z_index: 50
          opacity: 0.6
      
      # Ambient sound
      - media_id: "dragon_rumble"
        media_path: "assets/audio/dragon_breathing.mp3"
        media_role: "ambient_sound"
        staging_hints:
          loop: true
          volume: 0.3

# Result: 3 MediaFragments emitted during JOURNAL
# Service layer resolves all three and returns:
# {
#   "fragments": [
#     {
#       "fragment_type": "block",
#       "content": "You stand before..."
#     },
#     {
#       "fragment_type": "media",
#       "media_role": "narrative_im",
#       "url": "https://api/media/lair_abc.png",
#       "staging_hints": {"orientation": "landscape", ...}
#     },
#     {
#       "fragment_type": "media",
#       "media_role": "narrative_im",
#       "url": "https://api/media/dragon_xyz.png",
#       "staging_hints": {"opacity": 0.6, ...}
#     },
#     {
#       "fragment_type": "media",
#       "media_role": "ambient_sound",
#       "url": "https://api/media/rumble_def.mp3",
#       "staging_hints": {"loop": true, ...}
#     }
#   ]
# }
```

---

## Testing Strategy

### Unit Tests

```python
# test_media_resource.py
def test_media_rit_path_construction():
    """MediaRIT can be created from file path."""
    rit = MediaRIT(
        path="assets/image.png",
        media_type=MediaDataType.IMAGE
    )
    assert rit.uid
    assert rit.path == "assets/image.png"

def test_media_rit_content_hash():
    """MediaRIT deduplicates by content hash."""
    data = b"fake image bytes"
    rit1 = MediaRIT(data=data, media_type=MediaDataType.IMAGE)
    rit2 = MediaRIT(data=data, media_type=MediaDataType.IMAGE)
    assert rit1.content_hash == rit2.content_hash

# test_media_registry.py
def test_registry_dedupe_by_hash():
    """Registry avoids duplicate entries for same content."""
    registry = MediaResourceRegistry()
    rit1 = MediaRIT(data=b"test", media_type=MediaDataType.IMAGE)
    rit2 = MediaRIT(data=b"test", media_type=MediaDataType.IMAGE)
    
    registry.add(rit1)
    registry.add(rit2)
    
    assert len(list(registry)) == 1  # Only one entry

# test_media_provisioner.py
def test_provisioner_discovers_existing():
    """Provisioner finds existing RIT by identifier."""
    registry = MediaResourceRegistry()
    existing = MediaRIT(path="asset.png", media_type=MediaDataType.IMAGE)
    registry.add(existing, alias="tavern_bg")
    
    req = MediaRequirement(
        graph=graph,
        identifier="tavern_bg",
        policy=ProvisioningPolicy.EXISTING
    )
    
    provisioner = MediaProvisioner(
        requirement=req,
        registries=[registry]
    )
    
    offers = provisioner.generate_offers()
    assert len(offers) == 1
    assert offers[0].resource == existing
```

### Integration Tests

```python
# test_media_planning_integration.py
def test_media_dependency_provisioned_during_planning():
    """End-to-end: MediaDependency → PLANNING → bound RIT."""
    # 1. Create story with media dependency
    g = StoryGraph(label="test")
    block = Block(graph=g, label="test_block")
    
    req = MediaRequirement(
        graph=g,
        template={'media_path': 'test.png'},
        policy=ProvisioningPolicy.ANY
    )
    
    dep = MediaDependency(
        graph=g,
        source_id=block.uid,
        requirement=req
    )
    
    # 2. Run planning phase
    frame = Frame(graph=g, cursor_id=block.uid)
    planning_receipt = frame.run_phase(P.PLANNING)
    
    # 3. Verify dependency satisfied
    assert dep.is_satisfied()
    rit = dep.destination
    assert isinstance(rit, MediaRIT)
    assert rit.path == 'test.png'

# test_media_journal_integration.py
def test_block_emits_media_fragment():
    """End-to-end: Provisioned RIT → JOURNAL → MediaFragment."""
    # Setup provisioned media
    g = StoryGraph(label="test")
    block = Block(graph=g, label="test_block")
    rit = MediaRIT(path="test.png", media_type=MediaDataType.IMAGE)
    g.add(rit)
    
    dep = MediaDependency(
        graph=g,
        source_id=block.uid,
        destination_id=rit.uid,
        requirement=MediaRequirement(graph=g)
    )
    
    # Run JOURNAL phase
    frame = Frame(graph=g, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)
    
    # Verify MediaFragment emitted
    media_frags = [f for f in fragments if isinstance(f, MediaFragment)]
    assert len(media_frags) == 1
    assert media_frags[0].content == rit
```

---

## Glossary

**MediaResourceInventoryTag (MediaRIT):** Entity representing a media resource with indirection for path/data/spec storage. Analogous to how actors are entities that provision roles.

**MediaDependency:** DependencyEdge subclass linking structural nodes to media resources. Resolved during PLANNING phase.

**MediaRequirement:** Requirement subclass specifying how to obtain media (identifier, path, or spec).

**MediaProvisioner:** Provisioner subclass that discovers/creates MediaRIT to satisfy dependencies.

**MediaFragment:** ContentFragment subclass emitted during JOURNAL phase, containing MediaRIT reference.

**MediaSpec:** Abstract specification for generative media (Stable Diffusion, SVG paperdoll, TTS).

**MediaForge:** Handler that generates media from MediaSpec (registered with `on_create_media`).

**Dereferencing:** Service layer process of converting MediaRIT → client format (URL, Base64, path).

**Staging Hints:** Rendering metadata (orientation, placement, z-index) guiding client presentation.

**Media Role:** Semantic label (narrative_im, dialog_vo, ambient_music) indicating narrative intent.

**Content Hash:** Content-addressed identifier for deduplication and caching.

**Spec Hash:** Spec-addressed identifier for generative media caching.

---

## References

### Implementation Files

- **Media Resource:** `engine/src/tangl/media/media_resource/`
  - `media_resource_inv_tag.py` - MediaRIT entity
  - `media_resource_registry.py` - Registry
  - `media_dependency.py` - DependencyEdge
  - `media_provisioning.py` - Provisioner (needs modernization)

- **Media Creators:** `engine/src/tangl/media/media_creators/`
  - `media_spec.py` - Spec base class and dispatch
  - `stable_forge/` - Stable Diffusion implementation
  - `svg_forge/` - SVG paperdoll (stub)
  - `tts_forge/` - Text-to-speech (stub)

- **Journal:** `engine/src/tangl/journal/media/`
  - `media_fragment.py` - MediaFragment class
  - `staging_hints.py` - Rendering hints

### Test Files

- `engine/tests/media/test_media_fragment.py` (basic serialization)
- **TODO:** `engine/tests/media/test_media_provisioner.py`
- **TODO:** `engine/tests/vm/planning/test_media_planning.py`
- **TODO:** `engine/tests/service/test_media_dereferencing.py`

### Design Documents

- This document (authoritative for v3.7 media integration)
- `PLANNING_PROVISIONING_DESIGN_v37.md` (provisioning patterns)
- `SERVICE_LAYER_DESIGN_v37.md` (orchestrator and controller patterns)
- `engine/src/tangl/media/notes.md` (original vocabulary)
- `engine/src/tangl/media/notes_v32.md` (v3.2 legacy notes)

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 3.7.0 | Nov 2025 | Initial comprehensive design document for v3.7 framework integration |

---

**Document Status:** 🟡 **TARGET ARCHITECTURE**

This document describes the **intended design** for media subsystem integration with v3.7. Core infrastructure exists but critical gaps remain (provisioning wiring, service layer dereferencing). Implementation is in progress.

**Next Steps:**
1. Implement `MediaRequirement` subclass
2. Modernize `MediaProvisioner` to use v3.7 base class
3. Wire provisioner into `planning.py` handlers
4. Add Block/Concept media emission logic
5. Implement RuntimeController dereferencing
6. Comprehensive testing across full lifecycle
