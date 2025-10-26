# StoryTangl Web Client (v3.7)

Modern Vue 3 + TypeScript web interface for StoryTangl narrative engine, resurrected from legacy codebase and rebuilt with current best practices.

## 🎯 Project Status

**Current Phase:** MVP Feature Complete - Testing & Polish

The core application is **functionally complete** for basic story interaction. All essential components from the legacy web client have been successfully ported and modernized.

---

## ✅ Completed Infrastructure

### Core Setup
- ✅ Vue 3.5 + Composition API
- ✅ Vuetify 3.7 with Material Design Icons
- ✅ TypeScript strict mode
- ✅ Vite 5 build system
- ✅ MSW v2 for API mocking (dev mode only)
- ✅ Vitest + Vue Test Utils
- ✅ ESLint + Prettier
- ✅ Path aliases (@/*)

### Global Utilities
- ✅ `useGlobal()` composable
  - Axios HTTP client with interceptors
  - `remapURL()` - URL resolution for media
  - `makeMediaDict()` - media array transformation
  - Debug/verbose flags from environment
- ✅ Pinia store for global state
  - World selection
  - User authentication (API keys)
  - World info caching

### Type System
- ✅ Complete TypeScript definitions
- ✅ Types match backend Pydantic models
- ✅ `tangl_typedefs.ts` - core narrative types
- ✅ Environment variable typing

---

## ✅ Completed Components

### Layout Components
| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| `App.vue` | ✅ | Manual | Main layout with responsive drawer |
| `AppNavbar.vue` | ✅ | ✅ | Top bar with menus |
| `AppFooter.vue` | ✅ | - | Simple footer |

### Story Components
| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| `StoryFlow.vue` | ✅ | ✅ | Block container, API calls, auto-scroll |
| `StoryBlock.vue` | ✅ | ✅ | Text, media, dialog, actions |
| `StoryAction.vue` | ✅ | ✅ | Clickable choice buttons |
| `StoryDialogBlock.vue` | ✅ | ✅ | Character dialog with media |
| `StoryStatus.vue` | ✅ | - | Sidebar status display (key/value) |

### Dialog Components
| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| `WorldInfo.vue` | ✅ | - | World metadata modal |
| `SystemInfo.vue` | ✅ | - | System/engine info modal |
| `SecretDialog.vue` | ✅ | - | User authentication |

---

## 🚧 Known Gaps & Polish Items

### Missing Features (Non-Critical)
- ⏸️ **ApiDialog.vue** - Change API host (dev-only feature, low priority)
- ⏸️ **Custom branding** - BrandTangl icon component (cosmetic)
- ⏸️ **Keyboard shortcuts** - Not in legacy, but would be nice
- ⏸️ **Accessibility audit** - ARIA labels, focus management

### Testing Gaps
- ⚠️ **StoryAction.test.ts** - Needs comprehensive tests
- ⚠️ **StoryDialogBlock.test.ts** - Needs comprehensive tests
- ⚠️ **StoryStatus.test.ts** - Needs tests
- ⚠️ **Dialog components** - Need basic tests
- ⚠️ **Integration tests** - Full user flow tests

### Polish & UX
- ⚠️ **Loading states** - More granular feedback
- ⚠️ **Error boundaries** - Better error handling UI
- ⚠️ **Mobile responsive** - Some layout quirks
- ⚠️ **Media optimization** - Lazy loading, placeholders
- ⚠️ **Animations** - Smooth transitions

### Documentation
- ⚠️ **Component READMEs** - Usage examples for complex components
- ⚠️ **Storybook** - Interactive component showcase (optional)
- ⚠️ **API client docs** - How to extend endpoints

---

## 📋 Roadmap: What's Left

### Phase 1: Testing (Current Priority)
**Goal:** Achieve 80%+ test coverage on all components

- [ ] Write tests for `StoryAction.vue`
- [ ] Write tests for `StoryDialogBlock.vue`
- [ ] Write tests for `StoryStatus.vue`
- [ ] Write tests for dialog components (WorldInfo, SystemInfo, SecretDialog)
- [ ] Write integration tests for full story flow
- [ ] Add E2E tests with Playwright (optional)

**Estimated:** 1-2 days

---

### Phase 2: Polish & UX (Next)
**Goal:** Production-ready user experience

- [ ] Improve loading states and spinners
- [ ] Add error boundaries and fallback UI
- [ ] Audit mobile responsiveness
- [ ] Add smooth transitions/animations
- [ ] Optimize media loading (lazy load images)
- [ ] Keyboard navigation support
- [ ] Basic accessibility audit

**Estimated:** 2-3 days

---

### Phase 3: Documentation (Then)
**Goal:** Make codebase easy to maintain and extend

- [ ] Document component architecture
- [ ] Add JSDoc comments to all exports
- [ ] Create component usage examples
- [ ] Document common patterns
- [ ] API client extension guide
- [ ] Consider adding Storybook (optional)

**Estimated:** 1-2 days

---

### Phase 4: Advanced Features (Future)
**Goal:** Beyond MVP scope

- [ ] Vue Router for multi-page navigation
- [ ] Save/load game state
- [ ] Character sheets / inventory UI
- [ ] Settings panel (theme, text size, etc)
- [ ] Achievement system UI
- [ ] Replay/history browsing
- [ ] Social features (if applicable)

**Estimated:** TBD based on requirements

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
