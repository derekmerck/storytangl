import { useGlobal } from "@/globals";
const { $http, $debug } = useGlobal()

// App
import { createApp } from 'vue'
import App from './App.vue'
const app = createApp(App)

// Plugins
import { registerPlugins } from '@/plugins'
registerPlugins(app)

// msw mock endpoints
import { worker } from '../mocks/msw/worker'
console.log($debug.value)
console.log(import.meta.env.VITE_MOCK_RESPONSES)
if ($debug.value && import.meta.env.VITE_MOCK_RESPONSES === 'true' ) {
    console.log('starting msw')
    // leave the base path alone and mock with msw
    worker.start({
        onUnhandledRequest: 'bypass',
    })
} else {
    // todo: set basepath from url _or_ from localstorage if changed
    $http.value.defaults.baseURL = import.meta.env.VITE_DEFAULT_API_URL
}

// Mount
app.mount('#app')


