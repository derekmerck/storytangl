# WebTangl Quick Reference Card

## 🚀 Essential Commands

```bash
# Development
yarn dev              # Start dev server (localhost:5173)
yarn build           # Build for production
yarn preview         # Preview production build

# Testing
yarn test            # Run all tests once
yarn test --watch    # Watch mode (TDD)
yarn test:ui         # Visual test runner
yarn test:coverage   # Coverage report

# Code Quality
yarn type-check      # TypeScript validation
yarn lint            # Lint all files
yarn format          # Format all files

# API Types
yarn generate-api    # Generate types from OpenAPI spec
```

## 📁 Where Things Live

```
src/                   (@)
├── components/      → Vue components
│   ├── story/       → StoryBlock, StoryFlow, etc
│   ├── ui/          → Reusable UI components  
│   └── layout/      → AppNavbar, AppFooter
├── types/           → TypeScript types
├── store/           → Pinia state management
├── composables/     → useGlobal() etc
├── plugins/         → Vuetify, Router setup
└── styles/          → SCSS files
tests/               → Test setup & mocks (@tests)
```

## 🧪 Test Template (Copy/Paste Ready)

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import MyComponent from '@/components/MyComponent.vue'

const vuetify = createVuetify({ components, directives })

describe('MyComponent', () => {
  it('does something', () => {
    const wrapper = mount(MyComponent, {
      props: { /* props */ },
      global: { plugins: [vuetify] }
    })
    
    expect(wrapper.text()).toContain('expected')
  })
})
```

## 🎨 Vuetify Utility Classes

```html
<!-- Spacing -->
<div class="pa-4">        padding: 16px all sides
<div class="ma-2">        margin: 8px all sides
<div class="px-6">        padding: 24px left/right
<div class="mt-3">        margin-top: 12px

<!-- Display -->
<div class="d-flex">      display: flex
<div class="d-block">     display: block
<div class="d-none">      display: none

<!-- Flex -->
<div class="justify-center">   justify-content: center
<div class="align-center">     align-items: center
<div class="flex-column">      flex-direction: column

<!-- Text -->
<div class="text-h1">     heading 1 size
<div class="text-center"> text-align: center
<div class="text-primary">color: primary theme color

<!-- Elevation -->
<v-card elevation="2">    shadow level 0-24
```

## 🔧 TypeScript Quick Fixes

```typescript
// Type a prop
defineProps<{
  message: string
  count?: number
}>()

// Type an emit
const emit = defineEmits<{
  doAction: [uid: string, payload?: any]
}>()

// Type a ref
const loading = ref<boolean>(false)
const data = ref<MyType | null>(null)

// Type computed
const doubled = computed<number>(() => count.value * 2)
```

## 🎭 MSW Mock Override (in test)

```typescript
import { server } from '@/tests/setup'
import { http, HttpResponse } from 'msw'

it('handles custom response', async () => {
  server.use(
    http.get('/api/v2/story/update', () => {
      return HttpResponse.json([{ uid: '1', text: 'Custom' }])
    })
  )
  // test code
})
```

## 📊 Type Definitions Quick Ref

```
// Story types
JournalStoryUpdate {
  uid: string
  text?: string
  media?: JournalMediaItems
  actions?: JournalAction[]
  dialog?: StyledJournalItem[]
}

JournalAction {
  uid: string
  text: string
  icon?: string
  payload?: string
}

// Media types
MediaRole = 
  | 'narrative_im' | 'dialog_im' | 'avatar_im' 
  | 'info_im' | 'logo_im' | 'cover_im'
  | 'narrative_vox' | 'character_vox'
  | 'music' | 'sound_fx'

JournalMediaItem {
  media_role: MediaRole
  url?: string
  data?: unknown
}
```

## 🌐 API Endpoints

```
// Story
GET  /story/update           → RuntimeEnvelope
POST /story/do               → RuntimeEnvelope
GET  /story/info             → RuntimeInfo
POST /story/story/create     → RuntimeInfo + envelope

// System
GET  /system/info            → SystemStatus
GET  /system/worlds          → WorldList

// World
GET  /world/:id/info         → WorldInfo

// User
GET  /user/info              → UserInfo
POST /user/create            → UserSecretResponse
PUT  /user/secret            → UserSecretResponse
```

## 🎯 TDD Workflow

```
1. Write failing test
   └─► Red: Test fails as expected
   
2. Write minimal code to pass
   └─► Green: Test passes
   
3. Refactor if needed
   └─► Refactor: Improve code
   
4. Repeat
```

## 🔍 Debugging in PyCharm

```
Breakpoints:
- Click line number gutter (red dot)
- Run → Debug 'Dev Server'
- Browser triggers breakpoint
- Inspect variables in Debug panel

Vue DevTools:
- Install browser extension
- Opens in browser DevTools
- Inspect components, state, events
```

## 🎨 Vuetify Colors

```html
<!-- Text colors -->
<div class="text-primary">    theme primary color
<div class="text-secondary">  theme secondary color
<div class="text-error">      error red
<div class="text-success">    success green

<!-- Background colors -->
<div class="bg-primary">      background primary
<div class="bg-surface">      surface color

<!-- Variants -->
<v-btn color="primary">       filled primary
<v-btn color="primary" variant="outlined">
<v-btn color="primary" variant="text">
<v-btn color="primary" variant="tonal">
```

## ⚡ Hot Keys in Dev

```
Browser:
Ctrl+Shift+R    Hard refresh (clear cache)
Ctrl+Shift+I    Open DevTools
Ctrl+Shift+C    Inspect element

PyCharm:
Ctrl+Alt+S      Settings
Ctrl+Shift+F    Find in files
Ctrl+Shift+R    Replace in files
Alt+Shift+F10   Run configurations
F2              Navigate to error
Ctrl+Shift+F12  Maximize editor
```

## 📝 Git Workflow

```bash
# Before starting work
git checkout -b feature/story-block-component

# While working
git add src/components/story/StoryBlock.vue
git add src/components/story/StoryBlock.test.ts
git commit -m "feat: add StoryBlock component with tests"

# When done
git push origin feature/story-block-component
# Create PR on GitHub
```

## 🐛 Common Issues

```
Issue: Types not updating
Fix:  Restart TS service (PyCharm: Help → Find Action → Restart TS)

Issue: Vuetify components not styled
Fix:  Check @mdi/font installed, vuetify plugin loaded

Issue: Tests failing with mount errors
Fix:  Ensure vuetify plugin passed to wrapper

Issue: Hot reload not working
Fix:  Restart dev server (Ctrl+C, yarn dev)

Issue: Import path errors
Fix:  Use @ alias (e.g., @/components/...)
```

## 📊 Coverage Thresholds

```
Target coverage (aim for):
Statements:  80%+
Branches:    75%+  
Functions:   80%+
Lines:       80%+

Check with: yarn test:coverage
```

## 🎓 Key Patterns

```typescript
// Composables pattern
export function useMyFeature() {
  const state = ref()
  const doSomething = () => { }
  return { state, doSomething }
}

// Component composition
<script setup lang="ts">
import { useMyFeature } from '@/composables/myFeature'
const { state, doSomething } = useMyFeature()
</script>

// Store pattern (Pinia)
export const useStore = defineStore('main', {
  state: () => ({ count: 0 }),
  actions: {
    increment() { this.count++ }
  }
})
```

## 💡 Pro Tips

1. **Type first** - Define types before implementation
2. **Test first** - Write test, watch it fail, make it pass
3. **Small commits** - Commit working code frequently
4. **Name clearly** - Component names should describe purpose
5. **One concern** - Each component does one thing well
6. **Props down, events up** - Data flows down, events flow up
7. **Composition over inheritance** - Use composables, not mixins

## 📞 Help

```
Stuck? Check:
1. README.md           - Project overview
2. SETUP_GUIDE.md      - Installation & config
3. TESTING_PATTERNS.md - Testing recipes
4. ARCHITECTURE.md     - System design

Still stuck? Read the error message carefully - 
TypeScript and Vue give good hints!
```

---
💾 **Save this file** - Print it or keep on second monitor!
