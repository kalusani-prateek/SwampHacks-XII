import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import UserManagement from './pages/UserManagement'
import SiteManagement from './pages/SiteManagement'
import IncidentManagement from './pages/IncidentManagement'
import { useAuth } from './context/AuthContext'

function App() {
  const { user, loading, login, register, logout } = useAuth()

  if (loading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>
  }

  const handleLogout = async () => {
    await logout()
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        {!user && !loading ? (
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<Navigate to="/login" replace />} />
          </Routes>
        ) : (
          <>
            <header className="bg-white shadow-md">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                  <div className="flex">
                    <div className="flex-shrink-0 flex items-center">
                      <h1 className="text-xl font-semibold text-gray-800">SwampHacks XII</h1>
                    </div>
                    <div className="hidden md:block">
                      <div className="ml-10 flex items-baseline space-x-4">
                        <Link to="/dashboard" className="px-3 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-900">
                          Dashboard
                        </Link>
                        <Link to="/users" className="px-3 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-900">
                          Users
                        </Link>
                        <Link to="/sites" className="px-3 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-900">
                          Sites
                        </Link>
                        <Link to="/incidents" className="px-3 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-900">
                          Incidents
                        </Link>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center">
                    {user && (
                      <div className="mr-4 text-sm font-medium text-gray-700">
                        Welcome, {user.username}!
                      </div>
                    )}
                    <button onClick={handleLogout} className="px-3 py-2 bg-red-600 text-white font-medium rounded-md hover:bg-red-700">
                      Logout
                    </button>
                  </div>
                </div>
              </div>
            </header>
            <main>
              <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <Routes>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/users" element={<UserManagement />} />
                  <Route path="/sites" element={<SiteManagement />} />
                  <Route path="/incidents" element={<IncidentManagement />} />
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </div>
            </main>
          </>
        )}
      </div>
    </BrowserRouter>
  )
}

export default App