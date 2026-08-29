import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/token': 'http://localhost:8001',
      '/session': 'http://localhost:8001',
      '/llm-proxy': 'http://localhost:8001',
      '/cases': 'http://localhost:8001',
      '/mock': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
      '/chat': 'http://localhost:8001',
    }
  }
})
