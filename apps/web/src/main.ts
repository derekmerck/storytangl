// src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
// import { registerPlugins } from '@/plugins'
import { vuetify } from './plugins/vuetify'
import './styles/main.scss'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(vuetify)

// registerPlugins(app)

// Only in development mode AND when mocking is explicitly enabled
if (import.meta.env.DEV && import.meta.env.VITE_MOCK_RESPONSES === 'true') {
  console.log('🎭 Starting MSW mock server...')

  import('@tests/mocks/browser').then(({ worker }) => {
    worker.start({
      onUnhandledRequest: 'bypass',
    }).then(() => {
      console.log('✅ MSW mock server ready')
      app.mount('#app')
    })
  })
} else {
  app.mount('#app')
}
