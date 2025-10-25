import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

// Styles
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

// Theme configuration
const tanglTheme = {
  dark: true,
  colors: {
    primary: '#8B5CF6',      // Purple
    secondary: '#EC4899',    // Pink
    accent: '#06B6D4',       // Cyan
    error: '#EF4444',
    warning: '#F59E0B',
    info: '#3B82F6',
    success: '#10B981',
    background: '#1E1E1E',
    surface: '#2D2D2D',
  },
}

export const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: 'tanglTheme',
    themes: {
      tanglTheme,
    },
  },
  defaults: {
    VBtn: {
      variant: 'elevated',
      color: 'primary',
    },
    VCard: {
      elevation: 2,
    },
  },
})
