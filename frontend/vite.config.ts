import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// Dev proxies /api and /assets to the FastAPI backend so the browser sees a
// single origin (no CORS needed locally). Production uses VITE_API_BASE + CORS.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/assets': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
