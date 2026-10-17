// Vite build configuration.
// - @vitejs/plugin-react: JSX + fast refresh
// - @tailwindcss/vite:    Tailwind CSS v4 (no tailwind.config.js / postcss config needed)
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        // Libraries in their own files: smaller app bundle, and browsers keep them cached between releases.
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          map: ['leaflet', 'react-leaflet'],
        },
      },
    },
  },
  server: {
    port: 5173,
    // REST API PLACEHOLDER: when the Flask backend is running, requests to /api
    // are proxied to it so the session cookie stays same-origin in development.
    proxy: {
      '/api': 'http://localhost:5000',
    },
  },
});
