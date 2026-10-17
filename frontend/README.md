# SwampHacks XII Frontend

This is a React + Vite frontend with Tailwind CSS for the SwampHacks XII Flask REST API.

## Features

- Authentication (Login/Register)
- Dashboard with statistics
- User Management (View, Add, Edit, Delete)
- Site Management (View, Add, Edit, Delete)
- Incident Management (View, Add, Edit, Delete)
- Proxy configured to avoid CORS issues
- Responsive design with Tailwind CSS

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Make sure the backend is running on `http://localhost:5000`

## API Proxy

The frontend is configured to proxy all `/api/*` requests to `http://localhost:5000` via Vite's proxy setting in `vite.config.js`. This avoids CORS issues during development.

## Backend Changes Made

To enable proper user state management, the following changes were made to the backend:

1. **Removed CORS configuration** from `backend/run.py` (to use proxy architecture instead)
2. **Added GET /api/users/me endpoint** to the user blueprint in `backend/app/routes.py` to fetch current user's data

## Available Routes

### Authentication
- POST `/api/auth/register` - Register a new user
- POST `/api/auth/login` - Login user
- POST `/api/auth/logout` - Logout user

### User Management
- GET `/api/users/me` - Get current user's data
- GET `/api/users/<user_id>` - Get specific user's data
- PUT `/api/users/<user_id>` - Update specific user's data
- DELETE `/api/users/<user_id>` - Delete specific user's data

### Admin Only
- GET `/api/admins/users` - Get all users (admin required)
- GET `/api/admins/users/<user_id>` - Get specific user (admin required)
- PUT `/api/admins/users/<user_id>` - Update user (admin required)
- DELETE `/api/admins/users/<user_id>` - Delete user (admin required)

### Site Management
- POST `/api/sites/add_site` - Add new site (admin required)
- GET `/api/sites/get_sites` - Get all sites (no auth required)
- PUT `/api/sites/<site_id>` - Update site (admin required)
- DELETE `/api/sites/<site_id>` - Delete site (admin required)

### Incident Management
- POST `/api/incidents/add_incident` - Report new incident (login required)
- GET `/api/incidents/get_incidents` - Get all incidents (no auth required)
- PUT `/api/incidents/<incident_id>` - Update incident (login required, owner only)
- DELETE `/api/incidents/<incident_id>` - Delete incident (login required, owner only)