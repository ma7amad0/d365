import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: 'index.html',
        authRedirect: 'auth-redirect.html',
      },
    },
  },
  server: { proxy: { '/api': 'http://backend:8000', '/health': 'http://backend:8000' } },
})
