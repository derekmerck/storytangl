// Plugins
// import { loadFonts } from './webfontloader'
import { vuetify } from './vuetify'

// Pinia
import { createPinia } from "pinia";
const pinia = createPinia()

// import VueCookies from 'vue3-cookies'

export function registerPlugins (app) {
  // loadFonts()
  app
    .use(vuetify)
    .use(pinia)
    // .use(VueCookies)
}
