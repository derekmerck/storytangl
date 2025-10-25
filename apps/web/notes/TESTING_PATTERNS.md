# Testing Patterns Quick Reference

## Component Testing Template

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import YourComponent from '@/components/YourComponent.vue'

const vuetify = createVuetify({ components, directives })

describe('YourComponent', () => {
  it('renders correctly', () => {
    const wrapper = mount(YourComponent, {
      global: { plugins: [vuetify] },
      props: { /* your props */ },
    })
    
    expect(wrapper.text()).toContain('expected text')
  })
})
```

## Testing Props

```typescript
it('displays the prop value', () => {
  const wrapper = mount(Component, {
    props: { message: 'Hello' },
    global: { plugins: [vuetify] },
  })
  
  expect(wrapper.text()).toContain('Hello')
})
```

## Testing Events

```typescript
it('emits event when clicked', async () => {
  const wrapper = mount(Component, {
    global: { plugins: [vuetify] },
  })
  
  await wrapper.find('button').trigger('click')
  
  expect(wrapper.emitted()).toHaveProperty('customEvent')
  expect(wrapper.emitted().customEvent[0]).toEqual(['payload'])
})
```

## Testing with Pinia Store

```typescript
import { setActivePinia, createPinia } from 'pinia'
import { useStore } from '@/store'

describe('Component with store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('uses store data', () => {
    const store = useStore()
    store.someValue = 'test'
    
    const wrapper = mount(Component, {
      global: { 
        plugins: [vuetify, createPinia()],
      },
    })
    
    expect(wrapper.text()).toContain('test')
  })
})
```

## Mocking API Calls (MSW)

### Basic Mock
```typescript
import { server } from '@/tests/setup'
import { http, HttpResponse } from 'msw'

it('handles API response', async () => {
  server.use(
    http.get('/api/v2/story/update', () => {
      return HttpResponse.json([{ uid: '1', text: 'Custom response' }])
    })
  )
  
  // Test component that makes the API call
})
```

### Mock Error Response
```typescript
it('handles API error', async () => {
  server.use(
    http.get('/api/v2/story/update', () => {
      return new HttpResponse(null, { status: 500 })
    })
  )
  
  // Test error handling
})
```

## Testing Async Operations

```typescript
it('waits for async operation', async () => {
  const wrapper = mount(Component, {
    global: { plugins: [vuetify] },
  })
  
  await wrapper.find('button').trigger('click')
  await wrapper.vm.$nextTick() // Wait for DOM updates
  
  expect(wrapper.find('.result').text()).toBe('loaded')
})
```

## Testing Computed Properties

```typescript
it('computes value correctly', () => {
  const wrapper = mount(Component, {
    props: { count: 5 },
    global: { plugins: [vuetify] },
  })
  
  expect(wrapper.vm.doubleCount).toBe(10)
})
```

## Testing Slots

```typescript
it('renders slot content', () => {
  const wrapper = mount(Component, {
    slots: {
      default: 'Slot content',
      header: '<h1>Header slot</h1>',
    },
    global: { plugins: [vuetify] },
  })
  
  expect(wrapper.text()).toContain('Slot content')
})
```

## Testing v-model

```typescript
it('updates on input', async () => {
  const wrapper = mount(Component, {
    global: { plugins: [vuetify] },
  })
  
  const input = wrapper.find('input')
  await input.setValue('new value')
  
  expect(wrapper.vm.modelValue).toBe('new value')
})
```

## Snapshot Testing

```typescript
it('matches snapshot', () => {
  const wrapper = mount(Component, {
    props: { /* props */ },
    global: { plugins: [vuetify] },
  })
  
  expect(wrapper.html()).toMatchSnapshot()
})
```

## Testing with Router

```typescript
import { createRouter, createMemoryHistory } from 'vue-router'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [/* your routes */],
})

it('navigates on click', async () => {
  const wrapper = mount(Component, {
    global: { 
      plugins: [vuetify, router],
    },
  })
  
  await wrapper.find('a').trigger('click')
  expect(router.currentRoute.value.path).toBe('/expected-path')
})
```

## Best Practices

### ✅ Do
- Test behavior, not implementation
- Use descriptive test names
- Test edge cases and error states
- Mock external dependencies
- Keep tests isolated and independent
- Use `beforeEach` for common setup

### ❌ Don't
- Test framework internals (Vue/Vuetify)
- Test third-party library behavior
- Make tests dependent on each other
- Mock everything (test real integrations where valuable)
- Write brittle tests tied to DOM structure

## Coverage Goals

- **Statements**: 80%+
- **Branches**: 75%+
- **Functions**: 80%+
- **Lines**: 80%+

Run `yarn test:coverage` to check your coverage.

## Common Patterns for StoryTangl

### Testing Story Block Rendering
```typescript
it('renders story block with media', () => {
  const block = {
    uid: 'block-1',
    text: '<p>Story text</p>',
    media: [{ media_role: 'narrative_im', url: '/img.png' }],
  }
  
  const wrapper = mount(StoryBlock, {
    props: { block },
    global: { plugins: [vuetify] },
  })
  
  expect(wrapper.text()).toContain('Story text')
  expect(wrapper.find('img').attributes('src')).toBe('/img.png')
})
```

### Testing Action Buttons
```typescript
it('emits doAction when action clicked', async () => {
  const action = { uid: 'action-1', text: 'Do Something' }
  
  const wrapper = mount(StoryAction, {
    props: { action },
    global: { plugins: [vuetify] },
  })
  
  await wrapper.find('button').trigger('click')
  
  expect(wrapper.emitted().doAction[0]).toEqual(['action-1', undefined])
})
```

### Testing Media URL Remapping
```typescript
import { useGlobal } from '@/globals'

it('remaps relative URLs', () => {
  const { remapURL } = useGlobal()
  
  // Mock axios baseURL
  remapURL.value = (url: string) => {
    return url.startsWith('http') ? url : `http://localhost:8000${url}`
  }
  
  expect(remapURL('/media/test.png')).toBe('http://localhost:8000/media/test.png')
  expect(remapURL('http://example.com/test.png')).toBe('http://example.com/test.png')
})
```
