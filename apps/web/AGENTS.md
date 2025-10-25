# WebTangl Contributor Guide

Welcome! This is the web client for StoryTangl, built with Vue 3, Vuetify 3, and TypeScript. Use this guide as your quick reference for coding conventions, architecture patterns, and testing workflows.

## Repository layout
- `src/`: TypeScript source code with Vue components, composables, and stores
- `tests/`: Vitest tests and MSW mocks for API responses
- `public/`: Static assets (favicon, images, etc.)
- `notes/`: Developer documentation (architecture, guides, patterns)

## Coding style
- Target **TypeScript strict mode** with explicit types everywhere
- Use **Composition API** (`<script setup lang="ts">`) for all components
- Follow **Vue 3.5** conventions with `defineProps<>()` and `defineEmits<>()`
- Prefer **composables** over mixins - functions that return reactive state
- Keep **components small** - single responsibility, 100-200 lines max
- Use **Vuetify 3** utility classes over custom CSS when possible
- Follow **Prettier** formatting (2-space indent, single quotes, no semicolons)
- Keep lines under 100 characters when possible

## Component structure
Components follow this pattern:
```vue
<script setup lang="ts">
// 1. Imports
import { ref, computed } from 'vue'
import type { PropType } from 'vue'

// 2. Props with types
const props = defineProps<{
  block: JournalStoryUpdate
}>()

// 3. Emits with typed payloads
const emit = defineEmits<{
  doAction: [uid: string, payload?: any]
}>()

// 4. Composables
const { $http } = useGlobal()

// 5. Reactive state
const loading = ref(false)

// 6. Computed properties
const hasMedia = computed(() => props.block.media?.length > 0)

// 7. Methods
function handleClick() {
  emit('doAction', 'action-id')
}
</script>

<template>
  <!-- Vuetify components with utility classes -->
  <v-card class="pa-4">
    <v-card-text v-html="block.text" />
  </v-card>
</template>

<style scoped>
/* Only when Vuetify utilities aren't enough */
</style>
```

## File naming conventions
- Components: `PascalCase.vue` (e.g., `StoryBlock.vue`)
- Tests: `PascalCase.test.ts` (e.g., `StoryBlock.test.ts`)
- Composables: `camelCase.ts` with `use` prefix (e.g., `useGlobal.ts`)
- Types: `camelCase.ts` or `.d.ts` (e.g., `tangl_typedefs.ts`, `api.d.ts`)
- Stores: `camelCase.ts` (e.g., `store.ts`)

## Type definitions
- Keep types in `src/types/` directory
- Match backend Pydantic models in `tangl_typedefs.ts`
- Generate API types from OpenAPI spec: `yarn generate-api`
- Export types from `src/types/index.ts` for easy importing
- Use `type` imports: `import type { MyType } from '@/types'`

## Testing philosophy
- **Write tests first** (TDD) - red, green, refactor cycle
- **Test behavior, not implementation** - focus on user interactions
- **Use MSW for API mocking** - mock at network layer, not axios
- **Keep tests simple** - one assertion per test when possible
- **Test edge cases** - null props, empty arrays, error states

## Test template
```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import MyComponent from '@/components/MyComponent.vue'

const vuetify = createVuetify({ components, directives })

describe('MyComponent', () => {
  it('renders prop value', () => {
    const wrapper = mount(MyComponent, {
      props: { message: 'Hello' },
      global: { plugins: [vuetify] }
    })
    
    expect(wrapper.text()).toContain('Hello')
  })

  it('emits event on click', async () => {
    const wrapper = mount(MyComponent, {
      global: { plugins: [vuetify] }
    })
    
    await wrapper.find('button').trigger('click')
    
    expect(wrapper.emitted().customEvent).toBeTruthy()
  })
})
```

## Documentation
- Use **JSDoc comments** for exported functions and composables
- Add **README.md** to component directories for complex components
- Keep architecture docs in `notes/` directory
- See `notes/DOCUMENTATION.md` for full documentation strategy

## Core abstractions to understand
- **JournalStoryUpdate**: narrative block with text, media, and actions
- **JournalAction**: clickable action button with uid and optional payload
- **MediaRole**: semantic role for media (narrative_im, avatar_im, etc.)
- **StoryStatus**: key-value pairs for sidebar status display
- **useGlobal()**: composable providing $http, remapURL, makeMediaDict utilities

## Component architecture
```
App.vue (root)
├── AppNavbar (top bar)
│   ├── WorldInfo (dialog)
│   ├── SystemInfo (dialog)
│   └── SecretDialog (user auth)
├── v-navigation-drawer (sidebar)
│   └── StoryStatus (status display)
└── v-main (content area)
    └── StoryFlow (block container)
        └── StoryBlock (repeated)
            ├── StoryDialogBlock (optional, repeated)
            └── StoryAction (repeated)
```

## Data flow pattern
1. User clicks action button
2. StoryAction emits `doAction(uid, payload)`
3. StoryBlock passes event up
4. StoryFlow catches event
5. StoryFlow calls API via axios
6. Server returns JournalStoryUpdate[]
7. StoryFlow processes media URLs
8. StoryFlow appends blocks to reactive array
9. Vue reactivity updates DOM
10. Browser auto-scrolls to new content

## State management with Pinia
```typescript
export const useStore = defineStore('main', {
  state: () => ({
    current_world_uid: '',
    user_secret: '',
  }),
  actions: {
    async setCurrentWorld(world_uid: string) {
      this.current_world_uid = world_uid
      await this.getCurrentWorldInfo()
    }
  }
})
```

## API integration
- **Base URL**: Configured via `VITE_DEFAULT_API_URL` environment variable
- **Auth**: API key passed in `X-API-Key` header (from user secret)
- **Endpoints**: Match FastAPI routes (see `openapi.json`)
- **Mocking**: MSW handlers in `tests/mocks/handlers.ts`
- **Types**: Generated from OpenAPI spec or manually maintained

## Media handling
- **Media arrays** from API: `[{ media_role: 'narrative_im', url: '/media/img.png' }]`
- **Transform to dict**: `makeMediaDict()` converts to `{ narrative_im: { url, data } }`
- **URL remapping**: `remapURL()` converts relative to absolute URLs
- **Access pattern**: `block.media_dict?.narrative_im?.url`

## Environment variables
Create `.env.local` for development:
```bash
VITE_DEFAULT_API_URL=http://localhost:8000/api/v2
VITE_DEFAULT_WORLD=tangl_world
VITE_DEFAULT_USER_SECRET=dev-secret-123
VITE_DEBUG=true
VITE_MOCK_RESPONSES=false
VITE_SHOW_RESPONSES=true
```

## Testing and quality checks
- Run `yarn test` before committing changes
- Run `yarn type-check` to verify TypeScript types
- Run `yarn test:coverage` to check coverage (target: 80%+)
- Add tests in matching directory: `src/components/MyComponent.test.ts`
- Keep tests focused and fast - mock external dependencies

## Common commands
```bash
yarn dev              # Start dev server
yarn build            # Production build
yarn test             # Run tests once
yarn test --watch     # Watch mode for TDD
yarn test:ui          # Visual test runner
yarn test:coverage    # Coverage report
yarn type-check       # TypeScript validation
yarn lint             # Lint code
yarn format           # Format with Prettier
```

## Vuetify patterns
- Use **utility classes** for spacing: `pa-4` (padding all), `mt-2` (margin-top)
- Use **color classes**: `text-primary`, `bg-surface`
- Use **flex utilities**: `d-flex`, `justify-center`, `align-center`
- Prefer **v-row/v-col** over custom grid CSS
- Use **icons** from MDI: `<v-icon>mdi-heart</v-icon>`

## Composables pattern
Composables are reusable stateful logic:
```typescript
// useCounter.ts
export function useCounter(initial = 0) {
  const count = ref(initial)
  const double = computed(() => count.value * 2)
  
  function increment() {
    count.value++
  }
  
  return { count, double, increment }
}

// In component
const { count, increment } = useCounter(5)
```

## Error handling
- Use `try/catch` for async operations
- Display errors to user via Vuetify alerts
- Log errors for debugging: `console.error('Context:', error)`
- Provide fallback UI for error states
- Test error scenarios in component tests

## Performance tips
- Use `v-show` for toggling, `v-if` for conditional rendering
- Use `v-once` for static content
- Lazy load routes with dynamic imports
- Debounce expensive operations
- Use `key` attribute for list rendering

## Accessibility
- Use semantic HTML where possible
- Add `aria-label` to icon-only buttons
- Ensure keyboard navigation works
- Test with screen reader (VoiceOver/NVDA)
- Maintain color contrast ratios

## Build and deployment
- Production build: `yarn build` → outputs to `dist/`
- Preview build: `yarn preview`
- Assets in `public/` are copied as-is
- Environment variables prefixed with `VITE_` are exposed to client

## Git workflow
```bash
git checkout -b feature/component-name
# Make changes, add tests
git add .
git commit -m "feat: add ComponentName with tests"
git push origin feature/component-name
# Create pull request
```

## When introducing new features
- Start with failing test
- Implement minimal code to pass
- Refactor for clarity
- Update types if needed
- Add JSDoc comments
- Consider mobile/responsive design
- Test keyboard navigation
- Update relevant documentation

## Miscellaneous guidelines
- Avoid `any` type - use `unknown` and narrow with type guards
- Prefer `const` over `let`, avoid `var`
- Use optional chaining: `obj?.prop?.nested`
- Use nullish coalescing: `value ?? defaultValue`
- Extract magic numbers/strings to constants
- Keep template logic minimal - move complexity to script

Thanks for contributing to WebTangl!
