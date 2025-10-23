# StoryTangl Web Client - Clean Development Setup

## 📦 What You've Got

All files are ready in `/home/claude/`. This is a **complete, test-driven, TypeScript-strict** development environment for your Vue 3 + Vuetify 3 web client.

### File Manifest

```
/home/claude/
├── SETUP_GUIDE.md           ⭐ START HERE - Complete installation guide
├── TESTING_PATTERNS.md      📚 Testing recipes and best practices
├── reset-web-env.sh         🧹 Environment cleanup script
├── package.json             📦 Dependencies with testing tools
├── tsconfig.json            ⚙️  TypeScript strict mode config
├── vite.config.ts           ⚙️  Vite with Vuetify plugin
├── .eslintrc.cjs            🔍 Linting rules
├── .prettierrc              💅 Code formatting
├── .gitignore               🚫 Git exclusions
├── index.html               🌐 Entry HTML
└── src/
    ├── main.ts              🎯 App entry point
    ├── App.vue              👋 Hello World component
    ├── App.test.ts          ✅ Example test
    ├── vite-env.d.ts        📝 Environment types
    ├── plugins/
    │   └── vuetify.ts       🎨 Vuetify configuration (FIXED!)
    ├── styles/
    │   └── settings.scss    🎨 Vuetify SCSS customization
    └── tests/
        ├── setup.ts         🔧 Vitest + MSW setup
        └── mocks/
            ├── handlers.ts  🎭 MSW API handlers
            └── mockData.ts  📊 Mock API responses
```

## 🎯 Key Improvements Over Old Code

### Fixed Issues
1. ✅ **Vuetify plugin properly configured** (was broken)
2. ✅ **TypeScript strict mode enabled** (was off)
3. ✅ **Testing infrastructure complete** (was incomplete)
4. ✅ **MSW v2 for API mocking** (old code had v1)
5. ✅ **Latest dependencies** (Vue 3.5, Vuetify 3.7, Vite 5)

### New Capabilities
1. ✅ **Component testing with Vitest** (fast, built into Vite)
2. ✅ **API mocking with MSW** (matches your OpenAPI spec)
3. ✅ **Type-safe environment variables**
4. ✅ **ESLint + Prettier** (code quality from day 1)
5. ✅ **Coverage reporting** (track test coverage)

## 🚀 Quick Start (5 Minutes)

### Step 1: Copy Files
```bash
# From your project root
cd apps/web

# Copy all config files
cp /home/claude/{package.json,tsconfig.json,vite.config.ts,.eslintrc.cjs,.prettierrc,.gitignore,index.html} .

# Copy source files
cp -r /home/claude/src/* src/
```

### Step 2: Install
```bash
yarn install
```

### Step 3: Verify
```bash
# Type check (should pass)
yarn type-check

# Run tests (should pass)
yarn test

# Start dev server
yarn dev
```

### Step 4: Check Browser
Open `http://localhost:5173` - you should see the Hello World page!

## 📖 Read Next

1. **SETUP_GUIDE.md** - Detailed installation and PyCharm configuration
2. **TESTING_PATTERNS.md** - How to write tests for your components
3. Then come back here for the development roadmap

## 🗺️ Development Roadmap

Now that you have a clean slate, here's the recommended build order:

### Phase 1: Core Infrastructure (Week 1)
- [ ] Set up axios with typed API client
- [ ] Create proper auth flow (user secret → API key)
- [ ] Add Vue Router with basic structure
- [ ] Create global error handling
- [ ] Add loading states

### Phase 2: Story Components (Week 2)
- [ ] **StoryBlock component** (with tests)
  - Media rendering with role-based logic
  - Text/HTML content display
  - Dialog blocks
- [ ] **StoryAction component** (with tests)
  - Action buttons with icons
  - Event emission
- [ ] **StoryFlow component** (with tests)
  - Fragment streaming
  - Auto-scroll behavior
  - Block accumulation

### Phase 3: UI Components (Week 3)
- [ ] **AppNavbar** (with tests)
  - World selector
  - User menu
  - Settings
- [ ] **StoryStatus** (with tests)
  - Status display
  - Icon rendering
- [ ] **WorldInfo/SystemInfo** (with tests)
  - Info dialogs
  - Media display

### Phase 4: State & Integration (Week 4)
- [ ] Pinia store with proper typing
- [ ] Connect to real FastAPI backend
- [ ] Media URL handling
- [ ] Error boundaries
- [ ] Integration tests

### Phase 5: Polish (Week 5+)
- [ ] Mobile responsive design
- [ ] Keyboard shortcuts
- [ ] Accessibility improvements
- [ ] Save/load functionality
- [ ] Settings panel
- [ ] Character sheets/inventory

## 💡 Development Tips

### Testing Philosophy
**Write tests FIRST, then implement:**

1. Write test describing behavior you want
2. Run test (it fails - RED)
3. Implement minimal code to pass test (GREEN)
4. Refactor if needed (REFACTOR)
5. Repeat

Example workflow:
```typescript
// 1. Write test (fails)
it('renders story text', () => {
  expect(wrapper.text()).toContain('Story content')
})

// 2. Make it pass (minimal code)
<template>
  <div>{{ block.text }}</div>
</template>

// 3. Refactor (improve without breaking tests)
<template>
  <v-card>
    <v-card-text v-html="block.text" />
  </v-card>
</template>
```

### TypeScript Tips
- Run `yarn type-check` frequently
- Fix type errors immediately (don't accumulate)
- Use `any` only as last resort (add `// @ts-expect-error` comment explaining why)
- Let TypeScript catch bugs before runtime

### MSW Mock Strategy
- Keep mocks in `src/tests/mocks/`
- One mock per API endpoint
- Use realistic data that matches your types
- Override mocks in individual tests when needed

### Component Organization
```
components/
├── story/           # Story-specific components
│   ├── StoryBlock.vue
│   ├── StoryBlock.test.ts
│   ├── StoryAction.vue
│   └── StoryAction.test.ts
├── ui/              # Reusable UI components
│   ├── LoadingSpinner.vue
│   └── ErrorAlert.vue
└── layout/          # Layout components
    ├── AppNavbar.vue
    └── AppFooter.vue
```

## 🧪 Testing Commands

```bash
# Run all tests once
yarn test

# Run tests in watch mode (TDD)
yarn test --watch

# Run tests with UI (visual test runner)
yarn test:ui

# Generate coverage report
yarn test:coverage

# Type check only
yarn type-check

# Lint code
yarn lint

# Format code
yarn format
```

## 🎨 Styling Approach

### Vuetify Classes (Preferred)
Use Vuetify's utility classes:
```vue
<v-card class="pa-4 ma-2 elevation-2">
  <v-card-title class="text-h5 text-primary">
    Title
  </v-card-title>
</v-card>
```

### Scoped Styles (When Needed)
```vue
<style scoped>
.custom-class {
  /* Your custom styles */
}
</style>
```

### Theme Customization
Edit `src/plugins/vuetify.ts` to change colors:
```typescript
colors: {
  primary: '#YOUR_COLOR',
  secondary: '#YOUR_COLOR',
}
```

## 🐛 Common Issues & Solutions

### "Cannot find module @/something"
- Restart TypeScript service in PyCharm
- Check `tsconfig.json` has correct paths
- Verify file exists at expected location

### Tests failing with Vuetify errors
- Make sure you're passing `vuetify` plugin in test
- Check the test template in TESTING_PATTERNS.md

### Types not updating
- Restart TypeScript service
- Run `yarn type-check` to see actual errors
- Check `src/vite-env.d.ts` for environment types

### Hot reload not working
- Check Vite dev server is running
- Try hard refresh (Ctrl+Shift+R)
- Restart dev server

## 📚 Documentation References

- **Vue 3**: https://vuejs.org/guide/
- **Vuetify 3**: https://vuetifyjs.com/
- **Vitest**: https://vitest.dev/
- **MSW**: https://mswjs.io/
- **Vue Test Utils**: https://test-utils.vuejs.org/

## 🎓 Learning Resources

If you're rusty on any of these:

- **Vue Composition API**: https://vuejs.org/guide/extras/composition-api-faq.html
- **TypeScript with Vue**: https://vuejs.org/guide/typescript/overview.html
- **Vitest Testing**: https://vitest.dev/guide/
- **Component Testing**: https://test-utils.vuejs.org/guide/

## ✅ Success Checklist

Before you start building features:

- [ ] All files copied from `/home/claude/` to `apps/web/`
- [ ] `yarn install` completed successfully
- [ ] `yarn type-check` passes with no errors
- [ ] `yarn test` passes (3/3 tests)
- [ ] `yarn dev` starts and shows Hello World at localhost:5173
- [ ] Hot reload works (edit App.vue, see instant update)
- [ ] PyCharm recognizes TypeScript types in .vue files
- [ ] You can run tests from PyCharm UI
- [ ] You've read SETUP_GUIDE.md and TESTING_PATTERNS.md

## 🎉 You're Ready!

Once all checkboxes are checked, you have a **production-ready development environment** with:
- Modern tooling
- Type safety
- Testing infrastructure
- Best practices baked in

**Next**: Pick a component from the Phase 2 roadmap and build it TDD-style!

## 💬 Questions?

Refer to:
1. **SETUP_GUIDE.md** for installation issues
2. **TESTING_PATTERNS.md** for testing questions
3. Config file comments for tool-specific details

Let's build something amazing! 🚀
