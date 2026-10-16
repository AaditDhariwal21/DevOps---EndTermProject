import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, Vite proxies /api to a locally running FastAPI.
// In containers, Nginx (and in Kubernetes, the Ingress) does the same job.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': process.env.VITE_API_PROXY ?? 'http://localhost:8000',
    },
  },
})
