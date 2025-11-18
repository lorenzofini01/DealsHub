import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,       // Fondamentale per Docker: ascolta su 0.0.0.0
    port: 3000,       // Forza la porta 3000 (invece della 5173)
    watch: {
      usePolling: true, // Opzionale: aiuta se l'hot-reload non funziona su Windows/WSL
    },
  },
})