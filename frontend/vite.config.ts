import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': new URL('./src', import.meta.url).pathname,
    },
  },
  server: {
    port: 5173,
    proxy: {
      // The API and websockets are proxied in development so the browser sees
      // one origin. Avoids CORS entirely and mirrors how nginx serves both in
      // production.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
  build: {
    // Students open this on cheap phones over weak connections, so the
    // heaviest libraries are split out and cached separately from app code.
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('recharts') || id.includes('d3-')) return 'charts'
          if (id.includes('react-router')) return 'react'
          if (id.includes('/react-dom/') || id.includes('/react/')) return 'react'
          if (id.includes('@tanstack')) return 'query'
        },
      },
    },
    chunkSizeWarningLimit: 700,
  },
})
