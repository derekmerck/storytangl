import { defineConfig } from '@playwright/test'
import smoke from './playwright.config'

export default defineConfig({
  ...smoke,
  testMatch: 'json-restart.spec.ts',
  webServer: undefined,
  timeout: 90_000,
  outputDir: 'test-results/json-restart',
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report/json-restart' }]],
})
