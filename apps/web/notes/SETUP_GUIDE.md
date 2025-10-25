# WebTangl Development Environment Setup

## 🎯 What We've Built

A modern, test-driven Vue 3 + TypeScript development environment with:

- ✅ **Vue 3.5** with Composition API
- ✅ **Vuetify 3.7** with proper plugin configuration
- ✅ **TypeScript strict mode** for type safety
- ✅ **Vitest** for fast unit testing
- ✅ **MSW (Mock Service Worker)** for API mocking
- ✅ **ESLint + Prettier** for code quality
- ✅ **Vue Test Utils** for component testing

## 📋 Prerequisites

- Node.js 18+ (check with `node --version`)
- Yarn or npm package manager
- PyCharm Professional (recommended) or WebStorm

## 🚀 Installation Steps

### 1. Clean the Environment

```bash
cd apps/web
bash ../../reset-web-env.sh
```

This removes:
- `node_modules/`
- Lock files (`yarn.lock`, `package-lock.json`)
- Build artifacts (`dist/`, `.vite/`)
- IDE caches

### 2. Copy New Configuration Files

Copy these files from `/home/claude/` to `apps/web/`:

```bash
# From /home/claude/ -> apps/web/
cp /home/claude/package.json apps/web/
cp /home/claude/tsconfig.json apps/web/
cp /home/claude/vite.config.ts apps/web/
cp /home/claude/.eslintrc.cjs apps/web/
cp /home/claude/.prettierrc apps/web/
cp /home/claude/index.html apps/web/
```

### 3. Create New Directory Structure

```bash
cd apps/web

# Create test directories
mkdir -p src/tests/mocks

# Copy test files
cp /home/claude/src/tests/setup.ts src/tests/
cp /home/claude/src/tests/mocks/handlers.ts src/tests/mocks/
cp /home/claude/src/tests/mocks/mockData.ts src/tests/mocks/

# Copy plugin configuration
cp /home/claude/src/plugins/vuetify.ts src/plugins/

# Copy hello world files
cp /home/claude/src/App.vue src/
cp /home/claude/src/App.test.ts src/
cp /home/claude/src/main.ts src/
```

### 4. Install Dependencies

```bash
yarn install
```

This will take 2-5 minutes depending on your connection.

### 5. Create Environment File

Create `.env.local` in `apps/web/`:

```bash
# Development settings
VITE_DEFAULT_API_URL=http://localhost:8000/api/v2
VITE_DEFAULT_WORLD=tangl_world
VITE_DEFAULT_USER_SECRET=dev-secret-123
VITE_DEBUG=true
VITE_MOCK_RESPONSES=false
VITE_SHOW_RESPONSES=true
```

## ✅ Verification Steps

### 1. Type Check (should pass with no errors)

```bash
yarn type-check
```

Expected output: `✓ Type checking completed successfully`

### 2. Run Tests (should pass all tests)

```bash
yarn test
```

Expected output:
```
✓ src/App.test.ts (3 tests) 
  ✓ App.vue
    ✓ renders hello message
    ✓ increments counter when button is clicked
    ✓ displays success alert

Test Files  1 passed (1)
Tests  3 passed (3)
```

### 3. Start Dev Server

```bash
yarn dev
```

Expected output:
```
VITE v5.4.10  ready in 543 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### 4. Open Browser

Navigate to `http://localhost:5173`

You should see:
- Purple "WebTangl v3.7" header
- "Hello StoryTangl!" message
- Working counter with increment button
- Green success alert

### 5. Test Hot Reload

While dev server is running, edit `src/App.vue`:
- Change `Hello StoryTangl!` to `Hello World!`
- Save the file
- Browser should update instantly without full reload

## 🎓 PyCharm Configuration

### 1. Open Project

1. Open PyCharm
2. File → Open → Select your `storytangl` root directory
3. Mark `apps/web` as source root (right-click → Mark Directory As → Sources Root)

### 2. Configure Node.js

1. Settings → Languages & Frameworks → Node.js
2. Set Node interpreter (should auto-detect)
3. Enable "Coding assistance for Node.js"

### 3. Configure TypeScript

1. Settings → Languages & Frameworks → TypeScript
2. TypeScript version: Should show version from node_modules
3. Enable "TypeScript Language Service"
4. Recompile on changes: ✓

### 4. Set Up Run Configurations

**Dev Server:**
1. Run → Edit Configurations → Add → npm
2. Name: "Dev Server"
3. Package.json: `apps/web/package.json`
4. Command: `run`
5. Scripts: `dev`

**Tests:**
1. Run → Edit Configurations → Add → npm
2. Name: "Run Tests"
3. Package.json: `apps/web/package.json`
4. Command: `run`
5. Scripts: `test`

**Type Check:**
1. Run → Edit Configurations → Add → npm
2. Name: "Type Check"
3. Package.json: `apps/web/package.json`
4. Command: `run`
5. Scripts: `type-check`

### 5. Enable Vue Support

1. Settings → Languages & Frameworks → Vue
2. Enable Vue.js: ✓
3. Should auto-detect `vuetify` components

## 🧪 Testing Workflow

### Run All Tests
```bash
yarn test
```

### Run Tests in Watch Mode
```bash
yarn test --watch
```

### Run Tests with UI
```bash
yarn test:ui
```

### Run Tests with Coverage
```bash
yarn test:coverage
```

Coverage report will be in `coverage/index.html`

## 🎯 Next Steps

Now that your environment is set up:

1. **Verify everything works** - Run through all verification steps
2. **Add your first real component** - We'll build the StoryBlock component with tests
3. **Connect to real API** - Set up axios and connect to your FastAPI backend
4. **Add routing** - Set up Vue Router for multiple views
5. **Migrate existing components** - Bring over your old components one by one with tests

## 🐛 Troubleshooting

### "Cannot find module" errors

Run:
```bash
rm -rf node_modules yarn.lock
yarn install
```

### Type errors in .vue files

Restart TypeScript language service:
- PyCharm: Help → Find Action → "Restart TypeScript Service"
- Or restart PyCharm

### Vuetify components not styled

Check that:
1. `@mdi/font` is installed
2. `src/plugins/vuetify.ts` exists and is imported in `main.ts`
3. Vite config includes `vite-plugin-vuetify`

### Tests failing

Check that:
1. `src/tests/setup.ts` exists
2. `vitest.config.ts` has correct setupFiles path
3. MSW handlers are properly defined

## 📚 Useful Commands Reference

| Command | Description |
|---------|-------------|
| `yarn dev` | Start development server |
| `yarn build` | Build for production |
| `yarn preview` | Preview production build |
| `yarn test` | Run tests once |
| `yarn test:ui` | Open Vitest UI |
| `yarn test:coverage` | Run tests with coverage |
| `yarn type-check` | Check TypeScript types |
| `yarn lint` | Lint code |
| `yarn format` | Format code with Prettier |

## 🎉 Success Criteria

You're ready to start building when:

- ✅ All tests pass
- ✅ Type checking completes with no errors
- ✅ Dev server runs and shows hello world
- ✅ Hot reload works when you edit files
- ✅ PyCharm shows no TypeScript errors in App.vue
- ✅ You can run tests in PyCharm's test runner

---

**Questions or issues?** Check the troubleshooting section or the detailed comments in the config files.
