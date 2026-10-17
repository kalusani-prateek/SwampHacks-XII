// Vite build configuration.
// - @vitejs/plugin-react: JSX + fast refresh
// - @tailwindcss/vite:    Tailwind CSS v4 (no tailwind.config.js / postcss config needed)
import net from 'node:net';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// The Flask development server (backend/run.py). 127.0.0.1 rather than
// "localhost", which can resolve to the IPv6 address Flask doesn't listen on.
const BACKEND_URL = 'http://127.0.0.1:5000';

/**
 * Dev server only: checks every 2 s whether the backend is accepting
 * connections and tells open pages when it comes up, so a page that fell back
 * to demo data switches to live data without a manual refresh (see main.jsx).
 * A plain TCP check, so a stopped backend doesn't fill this terminal with
 * proxy errors the way polling /api through the proxy would.
 */
function backendWatcher() {
  return {
    name: 'planit-backend-watcher',
    apply: 'serve',
    configureServer(server) {
      const { hostname, port } = new URL(BACKEND_URL);
      let wasUp = null;
      const check = () => {
        const socket = net.connect({ host: hostname, port: Number(port) });
        const settle = (isUp) => {
          socket.destroy();
          if (isUp && wasUp === false) server.ws.send('planit:backend-up');
          wasUp = isUp;
        };
        socket.once('connect', () => settle(true));
        socket.once('error', () => settle(false));
      };
      check();
      const timer = setInterval(check, 2000);
      timer.unref();
      server.httpServer?.once('close', () => clearInterval(timer));
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), backendWatcher()],
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
      '/api': BACKEND_URL,
    },
  },
});
