/// <reference types="vitest"/>
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import path from 'path'
import { fileURLToPath } from 'url'

// ES module equivalent of __dirname
const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // Vuetify plugin for auto-importing components
    vuetify({
      autoImport: true,
      styles: {
        configFile: 'src/styles/settings.scss',
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  css: {
    preprocessorOptions: {
      sass: {
        api: "modern-compiler",
        // Suppress Dart Sass legacy API deprecation warnings
        // silenceDeprecations: ['legacy-js-api'],
      },
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      // Optional: Proxy API requests during development
      // Uncomment if you want to avoid CORS issues
      // '/api': {
      //   target: 'http://localhost:8000',
      //   changeOrigin: true,
      // },
    },
  },
  test: {
    server: {
      deps: {
        inline: ['vuetify'],
      }
    },
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./tests/setup.ts'],
    css: true, // Process CSS files instead of stubbing them
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/tests/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData',
        '**/types',
      ],
    },
  }
})