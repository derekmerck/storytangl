import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from "path";

export default defineConfig({
    rootDir: '.',
    resolve: {
        alias: {
            '@': path.resolve(__dirname, '/src'),
        },
    },
    plugins: [vue()],
    test:{
        globals: true,
        environment: 'jsdom'
    }
})