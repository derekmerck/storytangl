/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_DEFAULT_API_URL: string
  readonly VITE_DEFAULT_WORLD: string
  readonly VITE_DEFAULT_USER_SECRET: string
  readonly VITE_DEBUG: string
  readonly VITE_VERBOSE: string
  readonly VITE_MOCK_RESPONSES: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
