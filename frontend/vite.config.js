import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/market': 'http://localhost:8000',
      '/orders': 'http://localhost:8000',
      '/portfolio': 'http://localhost:8000',
      '/strategies': 'http://localhost:8000',
      '/watchlist': 'http://localhost:8000',
      '/backtest': 'http://localhost:8000',
    },
  },
})
