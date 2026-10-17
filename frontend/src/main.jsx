// Application entry point: decides demo vs. live data, then mounts <App />.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import 'leaflet/dist/leaflet.css'; // Leaflet's base map styles
import './index.css'; // Tailwind + app theme
import App from './App.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import { detectBackend } from './api/client.js';
import { registerOfflineSupport } from './offline.js';

registerOfflineSupport();

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
