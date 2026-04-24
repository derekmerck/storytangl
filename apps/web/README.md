# StoryTangl Web Client

Modern Vue 3 + TypeScript web interface for the StoryTangl narrative engine.

## Project Status

**Current Phase:** v38-era client stabilization

The web client is useful for development and narrative-engine inspection, but it is
not a production-ready MVP. The v38 engine/service surface has moved faster than
these notes, fixtures, and mock payloads. This pass repairs the Vitest/MSW
harness enough for the current suites to collect and run while keeping the richer
canonical fixture rewrite deferred to issue #224.

---

## Current Infrastructure

### Core Setup
- Vue 3.5 + Composition API
- Vuetify 3.7 with Material Design Icons
- TypeScript strict mode
- Vite 5 build system
- happy-dom Vitest environment
- MSW v2 for API mocking
- Vue Test Utils
- ESLint + Prettier
- Path aliases (`@/*`)

### Global Utilities
- `useGlobal()` composable
  - Axios HTTP client with interceptors
  - `remapURL()` URL resolution for media
  - `makeMediaDict()` media array transformation
  - Debug/verbose flags from environment
- Pinia store for global state
  - World selection
  - User authentication (API keys)
  - World info caching

### Type System
- TypeScript definitions exist for the legacy/current client contract.
- Some fixtures and mocks still need to be reconciled with the canonical v38
  service payloads tracked by #224.
- `tangl_typedefs.ts` carries core narrative types.
- Environment variable typing is present.

---

## Component Inventory

### Layout Components
| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| `App.vue` | Maintained | Manual | Main layout with responsive drawer |
| `AppNavbar.vue` | Maintained | Basic | Top bar with menus |
| `AppFooter.vue` | Maintained | - | Simple footer; version defaults intentionally unchanged here |

### Story Components
| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| `StoryFlow.vue` | Maintained | Yes | Block container, API calls, auto-scroll |
| `StoryBlock.vue` | Maintained | Yes | Text, media, dialog, actions |
| `StoryAction.vue` | Maintained | Basic | Clickable choice buttons |
| `StoryDialogBlock.vue` | Maintained | Basic | Character dialog with media |
| `StoryStatus.vue` | Maintained | Basic | Sidebar status display |

### Dialog Components
| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| `WorldInfo.vue` | Maintained | Basic | World metadata modal |
| `SystemInfo.vue` | Maintained | Basic | System/engine info modal |
| `SecretDialog.vue` | Maintained | Basic | User authentication |

---

## Known Gaps

### Harness and Fixtures
- The current pass keeps `happy-dom` and minimally repairs the MSW setup.
- Canonical v38 fixture design and richer mock/story payload coverage are
  tracked by #224.
- Tests should assert user-visible behavior and service contract shape rather
  than legacy implementation details.

### Product and UX
- API-host switching, custom branding, keyboard shortcuts, and a full
  accessibility audit remain open design/product work.
- Loading states, error surfaces, mobile layout, and media behavior need a
  focused polish pass after the test harness is trustworthy.

### Documentation
- Component notes, API-client notes, and fixture recipes should be updated as
  the #224 work lands.

---

## Roadmap

### Phase 1: Harness and Fixtures
**Goal:** Trust the local web test suite again.

- [x] Repair happy-dom/MSW setup enough for current suites to run.
- [ ] Replace ad hoc mock payloads with canonical v38 fixtures (#224).
- [ ] Add/adjust integration tests around current service envelopes.

### Phase 2: Client Contract Review
**Goal:** Align UI data assumptions with the engine/service v38 contract.

- [ ] Review story update, projected status, media, world info, and system info
  payloads against backend response models.
- [ ] Remove stale legacy-only assumptions.
- [ ] Keep fixture data close to real authoring/runtime examples.

### Phase 3: Polish and Documentation
**Goal:** Make the client pleasant and maintainable once the contract is stable.

- [ ] Improve loading and error states.
- [ ] Audit mobile and accessibility behavior.
- [ ] Document common component and fixture patterns.

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Yarn or npm

### Installation
```bash
cd apps/web
yarn install
```

### Development
```bash
# Start with MSW mocks (no backend needed)
yarn dev

# TypeScript checking
yarn type-check

# Run tests
yarn test

# Run tests in watch mode
yarn test --watch
```

### Environment Setup
Create `.env.local`:
```bash
VITE_DEFAULT_API_URL=http://localhost:8000/api/v2
VITE_DEFAULT_WORLD=tangl_world
VITE_DEFAULT_USER_SECRET=dev-secret-123
VITE_DEBUG=true
VITE_VERBOSE=false
VITE_MOCK_RESPONSES=true  # Use MSW mocks
```

### Production Build
```bash
yarn build
yarn preview  # Test production build locally
```

---

## 🏗️ Architecture

### Component Hierarchy
```
App.vue
├── AppNavbar
│   ├── WorldInfo (dialog)
│   ├── SystemInfo (dialog)
│   └── SecretDialog (dialog)
├── v-navigation-drawer
│   └── StoryStatus
└── v-main
    └── StoryFlow
        └── StoryBlock (repeated)
            ├── StoryDialogBlock (optional)
            └── StoryAction (repeated)
```

### Data Flow
1. User clicks `StoryAction` button
2. Event bubbles up: `StoryAction` → `StoryBlock` → `StoryFlow`
3. `StoryFlow` calls API via `$http`
4. Server returns `JournalStoryUpdate[]`
5. `StoryFlow` processes media URLs and creates media dictionaries
6. New blocks appended to reactive array
7. Vue re-renders with new blocks
8. Auto-scroll to latest block

### State Management
- **Pinia Store** (`src/store/index.ts`)
  - Current world selection
  - User secret & API key
  - Cached world info
- **Composables** (`src/composables/`)
  - `useGlobal()` - shared utilities
  - Future: `useStory()`, `useMedia()`, etc.

### API Integration
- **Base URL:** Environment variable `VITE_DEFAULT_API_URL`
- **Auth:** API key in `X-API-Key` header
- **Mocking:** MSW intercepts requests in dev mode
- **Endpoints:** Match FastAPI OpenAPI spec

---

## 📚 Key Documentation

- **[ARCHITECTURE.md](notes/ARCHITECTURE.md)** - System design overview
- **[AGENTS.md](AGENTS.md)** - Contributor guide & conventions
- **[TESTING_PATTERNS.md](notes/TESTING_PATTERNS.md)** - Test recipes
- **[SETUP_GUIDE.md](notes/SETUP_GUIDE.md)** - Detailed installation
- **[QUICK_REFERENCE.md](notes/QUICK_REFERENCE.md)** - Cheat sheet

---

## 🧪 Testing Strategy

### Current Coverage
- **StoryFlow:** ✅ Comprehensive tests
- **StoryBlock:** ✅ Comprehensive tests
- **useGlobal:** ✅ Unit tests
- **Store:** ✅ Unit tests
- **AppNavbar:** ✅ Basic tests

### Testing Commands
```bash
yarn test              # Run all tests
yarn test --watch      # TDD mode
yarn test:ui           # Visual test runner
yarn test:coverage     # Coverage report
```

### Test Principles
- Write tests first (TDD)
- Test behavior, not implementation
- Use MSW for API mocking
- Keep tests simple and focused
- One assertion per test when possible

---

## 🎨 Styling

### Approach
1. **Vuetify utilities first** - Use built-in classes when possible
2. **Scoped styles second** - Component-specific CSS
3. **Theme customization** - Edit `src/plugins/vuetify.ts`

### Custom Fonts
Currently using Adobe Fonts:
- **Burnaby Stencil** - Titles
- **Tenby** - Body text (optional)

To customize, edit `App.vue` style section.

---

## 🔧 Development Tools

### VS Code Extensions (Recommended)
- Volar (Vue Language Features)
- TypeScript Vue Plugin
- ESLint
- Prettier

### PyCharm Setup
- Enable Vue.js plugin
- Set TypeScript service to use project version
- Configure ESLint and Prettier

---

## 📦 Build & Deployment

### Build for Production
```bash
yarn build
```

Outputs to `dist/` directory. Serve with any static file server.

### Docker (Example)
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## 🤝 Contributing

### Before Starting
1. Read [AGENTS.md](AGENTS.md) for conventions
2. Check [TESTING_PATTERNS.md](notes/TESTING_PATTERNS.md)
3. Set up environment per [SETUP_GUIDE.md](notes/SETUP_GUIDE.md)

### Workflow
1. Create feature branch
2. Write failing test
3. Implement feature
4. Ensure tests pass
5. Run `yarn type-check` and `yarn lint`
6. Create PR with description

### Code Style
- TypeScript strict mode
- Composition API with `<script setup>`
- Vue 3.5 conventions
- 100 char line limit
- 2-space indentation
- Single quotes

---

## 🐛 Troubleshooting

### Common Issues

**MSW not intercepting requests**
- Check `.env.local` has `VITE_MOCK_RESPONSES=true`
- Hard refresh browser (Ctrl+Shift+R)
- Check console for MSW startup logs

**TypeScript errors**
- Restart TS server in IDE
- Run `yarn type-check` to see all errors
- Check path aliases in `tsconfig.json`

**Tests failing**
- Ensure env vars are stubbed in tests
- Check Vuetify plugin is passed to mount
- Verify MSW server is started in test setup

**Hot reload not working**
- Restart dev server
- Check for syntax errors
- Verify Vite config is correct

---

## 📄 License

See main project LICENSE file.

---

## 🎉 Summary

**The web client MVP is essentially complete!** All core components from the legacy codebase have been successfully ported and modernized with:
- Modern Vue 3 + TypeScript architecture
- Comprehensive testing infrastructure
- Development-friendly tooling
- Clean, maintainable codebase

**Next priorities:** Fill testing gaps, polish UX, and prepare for production deployment.

---

**Questions? Check the `/notes` directory or review legacy code in `/scratch/legacy/web` for reference implementations.**
