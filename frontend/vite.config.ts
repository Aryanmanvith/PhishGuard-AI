import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// In development the browser talks to Vite (port 5173) and Vite forwards /api/* to the
// FastAPI backend (port 8000). That means no CORS problems while developing.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1', // bind IPv4 too: the default listens only on [::1] on some Windows setups
    port: 5173,
    strictPort: true, // fail loudly if 5173 is taken (CORS allow-list expects this port)
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    css: false,
  },
});
