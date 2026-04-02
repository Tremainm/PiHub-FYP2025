import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',   // simulate browser DOM
    globals: true,          // no need to import describe/it/expect in every file
    setupFiles: './src/test/setup.js',
  }
})
