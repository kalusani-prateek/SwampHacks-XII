// Application entry point: decides demo vs. live data, then mounts <App />.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import 'leaflet/dist/leaflet.css'; // Leaflet's base map styles
import './index.css'; // Tailwind + app theme
import App from './App.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import { detectBackend, isMockFallback } from './api/client.js';
import { registerOfflineSupport } from './offline.js';

registerOfflineSupport();

// Dev server only: Vite announces when the backend starts (backendWatcher in
// vite.config.js), so a page showing demo data reloads into live data.
if (import.meta.hot) {
  import.meta.hot.on('planit:backend-up', () => {
    if (isMockFallback()) window.location.reload();
  });
}

// REST API PLACEHOLDER: GET /api/meta decides whether the real backend is available.
detectBackend().then(() => {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </StrictMode>,
  );
});
