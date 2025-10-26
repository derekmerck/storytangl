# WebTangl Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (localhost:5173)                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                        App.vue                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │ │
│  │  │   Navbar     │  │   Drawer     │  │    Main      │      │ │
│  │  │              │  │              │  │              │      │ │
│  │  │ - WorldMenu  │  │ - Status     │  │ - StoryFlow  │      │ │
│  │  │ - UserMenu   │  │ - Stats      │  │              │      │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │ │
│  │                                        ▲                   │ │
│  │                                        │                   │ │
│  │                    ┌───────────────────┴─────────────┐     │ │
│  │                    │      StoryFlow                  │     │ │
│  │                    │  - Manages block list           │     │ │
│  │                    │  - Handles API calls            │     │ │
│  │                    │  - Auto-scrolls                 │     │ │
│  │                    └───────────────────┬─────────────┘     │ │
│  │                                        │                   │ │
│  │                    ┌───────────────────▼─────────────┐     │ │
│  │                    │     StoryBlock (repeated)       │     │ │
│  │                    │  - Text content                 │     │ │
│  │                    │  - Media display                │     │ │
│  │                    │  - Dialog blocks                │     │ │
│  │                    │  - Action buttons               │     │ │
│  │                    └───────────────────┬─────────────┘     │ │
│  │                                        │                   │ │
│  │                    ┌───────────────────▼─────────────┐     │ │
│  │                    │     StoryAction (repeated)      │     │ │
│  │                    │  - Button with icon             │     │ │
│  │                    │  - Emits doAction               │     │ │
│  │                    └─────────────────────────────────┘     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │ HTTP (axios)
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer (Dual Mode)                        │
│                                                                 │
│  Development:                    Production:                    │
│  ┌────────────────┐             ┌────────────────┐              │
│  │  MSW (Mock)    │             │  FastAPI       │              │
│  │  - handlers.ts │             │  Server        │              │
│  │  - mockData.ts │             │  (port 8000)   │              │
│  └────────────────┘             └────────────────┘              │
│                                                                 │
│  API Endpoints:                                                 │
│  - GET  /story/update     → [JournalStoryUpdate[]]              │
│  - POST /story/do         → [JournalStoryUpdate[]]              │
│  - GET  /story/status     → StoryStatus[]                       │
│  - GET  /system/info      → SystemStatus                        │
│  - GET  /world/:id/info   → WorldInfo                           │
└─────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                      State Management (Pinia)                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  useStore()                                                │ │
│  │  - current_world_uid                                       │ │
│  │  - current_world_info                                      │ │
│  │  - user_secret                                             │ │
│  │  - user_api_key                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                     Global Utilities (Composables)              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  useGlobal()                                               │ │
│  │  - $http (axios instance)                                  │ │
│  │  - remapURL() - Fix relative URLs                          │ │
│  │  - makeMediaDict() - Transform media arrays                │ │
│  │  - $debug / $verbose - Dev flags                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
                         TYPE SYSTEM FLOW
═══════════════════════════════════════════════════════════════════

┌──────────────────┐
│  OpenAPI Spec    │ (from backend)
│  openapi.json    │
└─────────┬────────┘
          │
          │ (manual export, can automate later)
          ▼
┌──────────────────┐
│  TypeScript      │
│  types/          │
│  - api.d.ts      │ (generated)
│  - tangl_        │ (manual, matches backend models)
│    typedefs.ts   │
└─────────┬────────┘
          │
          │ imported by
          ▼
┌──────────────────┐
│  Components      │
│  - Props typed   │
│  - Events typed  │
│  - State typed   │
└──────────────────┘

═══════════════════════════════════════════════════════════════════
                         TESTING FLOW
═══════════════════════════════════════════════════════════════════

┌────────────────────────────────────────────────────────────────┐
│                    Developer writes test                       │
│  Component.test.ts                                             │
│  - Imports component                                           │
│  - Mounts with test utils                                      │
│  - Asserts behavior                                            │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│                    Vitest runs test                            │
│  - Loads setup.ts                                              │
│  - Initializes MSW server                                      │
│  - Executes test                                               │
└──────────────────────────┬─────────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
┌──────────────────┐            ┌──────────────────┐
│  Component needs │            │  Test assertions │
│  API data        │            │  check behavior  │
└─────────┬────────┘            └──────────────────┘
          │
          ▼
┌──────────────────┐
│  MSW intercepts  │
│  - Matches URL   │
│  - Returns mock  │
└──────────────────┘

═══════════════════════════════════════════════════════════════════
                         BUILD PROCESS
═══════════════════════════════════════════════════════════════════

Developer saves file (.vue, .ts)
          │
          ▼
┌──────────────────┐
│  Vite HMR        │ Hot Module Replacement
│  - Detects change│
│  - Rebuilds      │
│  - Updates       │
│    browser       │
└─────────┬────────┘
          │
          ▼
Browser updates without full reload (instant feedback!)

Production build:
┌──────────────────┐
│  yarn build      │
│  - TypeScript    │ → Compile & type check
│  - Vue SFC       │ → Compile to JS
│  - Vuetify       │ → Tree-shake & bundle
│  - Assets        │ → Optimize images, fonts
│  └→ dist/        │ → Ready to deploy
└──────────────────┘

═══════════════════════════════════════════════════════════════════
                    DIRECTORY STRUCTURE
═══════════════════════════════════════════════════════════════════

apps/web/
├── src/
│   ├── main.ts                     ← Entry point
│   ├── App.vue                     ← Root component
│   ├── vite-env.d.ts               ← Environment types
│   ├── components/
│   │   ├── story/                  ← Story-specific
│   │   │   ├── StoryFlow.vue
│   │   │   ├── StoryBlock.vue
│   │   │   └── StoryAction.vue
│   │   ├── ui/                     ← Reusable UI
│   │   │   └── ...
│   │   └── layout/                 ← Layout components
│   │       ├── AppNavbar.vue
│   │       └── AppFooter.vue
│   ├── plugins/
│   │   ├── index.ts                ← Plugin aggregator
│   │   └── vuetify.ts              ← Vuetify config
│   ├── store/
│   │   └── index.ts                ← Pinia store
│   ├── types/
│   │   ├── index.ts
│   │   ├── tangl_typedefs.ts       ← API types
│   │   └── api.d.ts                ← Generated
│   ├── styles/
│   │   └── settings.scss           ← Vuetify customization
│   ├── composables/
│   │   └── globals.ts              ← useGlobal()
│   └── tests/
│       ├── setup.ts                ← Test initialization
│       └── mocks/
│           ├── handlers.ts         ← MSW handlers
│           └── mockData.ts         ← Mock responses
├── public/                          ← Static assets
├── index.html                       ← Entry HTML
├── vite.config.ts                   ← Vite configuration
├── tsconfig.json                    ← TypeScript config
├── package.json                     ← Dependencies
└── .env.local                       ← Environment vars

═══════════════════════════════════════════════════════════════════
                    DATA FLOW EXAMPLE
═══════════════════════════════════════════════════════════════════

User clicks action button:
  │
  ├─► StoryAction.vue emits 'doAction' with (uid, payload)
  │
  ├─► StoryBlock.vue catches event, passes up
  │
  ├─► StoryFlow.vue catches event
  │     │
  │     ├─► Calls axios.post('/story/do', {uid, payload})
  │     │
  │     ├─► Receives JournalStoryUpdate[]
  │     │
  │     ├─► Processes media URLs with remapURL()
  │     │
  │     ├─► Transforms media[] → media_dict{}
  │     │
  │     ├─► Appends new blocks to blocks[]
  │     │
  │     └─► Vue reactivity updates DOM
  │
  └─► StoryBlock components render new content
        │
        └─► Browser auto-scrolls to new content

═══════════════════════════════════════════════════════════════════
                    KEY DESIGN DECISIONS
═══════════════════════════════════════════════════════════════════

✓ Client is THIN - server does heavy lifting
  - Client just renders and routes events
  - Server manages state, game logic, content

✓ Fragment-based streaming
  - Server returns journal fragments
  - Client accumulates and displays
  - Allows for complex narrative flows

✓ Media role system
  - Backend tags media with semantic roles
  - Client uses roles to determine rendering
  - Flexible: same media, different presentations

✓ Type-safe communication
  - TypeScript types match Python Pydantic models
  - Compile-time validation of API contracts
  - Reduces integration bugs

✓ Test-driven development
  - Tests written before implementation
  - Mocks based on real API spec
  - Confidence in refactoring

═══════════════════════════════════════════════════════════════════
```