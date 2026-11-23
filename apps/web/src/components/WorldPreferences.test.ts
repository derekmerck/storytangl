import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import WorldPreferences from './WorldPreferences.vue'
import { useStore } from '@/store'
import { server } from '@tests/setup'
import { reparteePreferencesInfo } from '@tests/fixtures'
import type { UiPreferencesValue } from '@/types'

const vuetify = createVuetify({ components, directives })
const declared = (reparteePreferencesInfo.sections[0]!.value as UiPreferencesValue).preferences

const mountPreferences = () => {
  setActivePinia(createPinia())
  const store = useStore()
  store.current_world_uid = 'repartee_loop'
  store.world_preferences = declared
  store.preference_values = { 'sprites-visible': true, 'clerk-motion': 'idle' }
  const wrapper = mount(WorldPreferences, { global: { plugins: [vuetify] } })
  return { store, wrapper }
}

describe('WorldPreferences', () => {
  it('renders nothing for a world that declares no preferences', () => {
    setActivePinia(createPinia())
    const wrapper = mount(WorldPreferences, { global: { plugins: [vuetify] } })

    expect(wrapper.find('[data-testid="world-preferences"]').exists()).toBe(false)
  })

  it('toggles a boolean and picks an enum value locally, without a request', async () => {
    const requests: string[] = []
    server.events.on('request:start', ({ request }) => requests.push(request.url))
    const { store, wrapper } = mountPreferences()

    expect(wrapper.text()).toContain('Decorative sprites')
    await wrapper.find('[data-preference="sprites-visible"] input').setValue(false)
    const call = wrapper
      .findAll('[data-preference="clerk-motion"] button')
      .find((button) => button.text() === 'call')!
    await call.trigger('click')

    expect(store.preference_values).toEqual({ 'sprites-visible': false, 'clerk-motion': 'call' })
    expect(requests).toEqual([])
    server.events.removeAllListeners()
  })
})
