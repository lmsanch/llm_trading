import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow access via Tailscale IP
    port: 4173,       // Use consistent port
    strictPort: true,  // Don't try other ports if 4173 is taken
    proxy: {
      '/api': {
        target: 'http://localhost:8200',
        changeOrigin: true,
      },
    },
  },
})
