// eslint.config.js
import js from '@eslint/js'
import typescript from '@typescript-eslint/eslint-plugin'
import typescriptParser from '@typescript-eslint/parser'
import vue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'

export default [
  // Ignore patterns (replaces .gitignore)
  {
    ignores: [
      'dist/',
      'dist-ssr/',
      'node_modules/',
      'coverage/',
      '*.local',
      '.vite'
    ]
  },

  // JavaScript/TypeScript base config
  js.configs.recommended,

  // Main config for all files
  {
    files: ['**/*.{js,mjs,cjs,ts,tsx,vue}'],
    plugins: {
      '@typescript-eslint': typescript,
      vue
    },
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: typescriptParser,
        ecmaVersion: 'latest',
        sourceType: 'module'
      }
    },
    rules: {
      // Customize as needed
      '@typescript-eslint/no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_'
      }],
      'vue/multi-word-component-names': 'off',
      'no-undef': 'off' // TypeScript handles this
    }
  },

  // Vue-specific rules
  ...vue.configs['flat/recommended'],
]