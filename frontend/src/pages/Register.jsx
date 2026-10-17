import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    site_id: ''
  })
  const [sites, setSites] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [siteLoading, setSiteLoading] = useState(true)

  // Fetch sites for dropdown
  React.useEffect(() => {
    fetch('/api/sites/get_sites')
      .then(res => res.json())
      .then(data => {
        setSites(Array.isArray(data) ? data : [])
        setSiteLoading(false)
      })
      .catch(() => {
        setSiteLoading(false)
      })
  }, [])

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const result = await register(formData)
      if (result.success) {
        navigate('/login')
      } else {
        setError(result.error || 'Registration failed')
      }
    } catch (err) {
      setError('An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Already have an account?
            <a href="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
              Sign in
            </a>
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="username" className="sr-only">Username</label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                value={formData.username}
                onChange={handleChange}
                placeholder="Username"
              />
            </div>
            <div>
              <label htmlFor="email" className="sr-only">Email</label>
              <input
                id="email"
                name="email"
                type="email"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                value={formData.email}
                onChange={handleChange}
                placeholder="Email"
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                value={formData.password}
                onChange={handleChange}
                placeholder="Password"
              />
            </div>
            <div>
              <label htmlFor="site_id" className="sr-only">Site</label>
              <select
                id="site_id"
                name="site_id"
                required
                className="appearance-none block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                value={formData.site_id}
                onChange={handleChange}
              >
                <option value="">Select a site</option>
                {siteLoading ? (
                  <option>Loading sites...</option>
                ) : (
                  sites.map(site => (
                    <option key={site.id} value={site.id}>
                      {site.name} ({site.city}, {site.state})
                    </option>
                    )
                  ))
                }
              </select>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </div>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-50 border-l-4 border-red-400 text-red-700">
            <p>{error}</p>
          </div>
        )}

        <p className="mt-6 text-center text-sm text-gray-500">
          © 2026 SwampHacks XII. All rights reserved.
        </p>
      </div>
    </div>
  )
}