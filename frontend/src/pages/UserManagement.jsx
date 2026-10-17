import React, { useState, useEffect } from 'react'

export default function UserManagement() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAddUser, setShowAddUser] = useState(false)
  const [showEditUser, setShowEditUser] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    is_admin: false,
    site_id: ''
  })
  const [sites, setSites] = useState([])
  const [siteLoading, setSiteLoading] = useState(true)

  // Fetch sites for dropdown
  useEffect(() => {
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

  // Fetch users
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const res = await fetch('/api/users')
        if (res.ok) {
          const data = await res.json()
          setUsers(Array.isArray(data.users) ? data.users : [])
        } else {
          throw new Error('Failed to fetch users')
        }
      } catch (err) {
        setError('Failed to load users')
      } finally {
        setLoading(false)
      }
    }

    fetchUsers()
  }, [])

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value === '' ? undefined :
        e.target.type === 'checkbox' ? e.target.checked : e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      let res
      if (editingUser) {
        // Update user
        res = await fetch(`/api/users/${editingUser.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify(formData)
        })
      } else {
        // Add user
        res = await fetch('/api/users', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify(formData)
        })
      }

      if (res.ok) {
        // Refresh users list
        const usersRes = await fetch('/api/users')
        if (usersRes.ok) {
          const usersData = await usersRes.json()
          setUsers(Array.isArray(usersData.users) ? usersData.users : [])
        }
        setShowAddUser(false)
        setShowEditUser(false)
        setEditingUser(null)
        setFormData({
          username: '',
          email: '',
          password: '',
          is_admin: false,
          site_id: ''
        })
      } else {
        const errorData = await res.json()
        setError(errorData.message || 'Operation failed')
      }
    } catch (err) {
      setError('Network error')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) {
      return
    }

    try {
      const res = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        credentials: 'include'
      })
      if (res.ok) {
        // Refresh users list
        const usersRes = await fetch('/api/users')
        if (usersRes.ok) {
          const usersData = await usersRes.json()
          setUsers(Array.isArray(usersData.users) ? usersData.users : [])
        }
      } else {
        const errorData = await res.json()
        setError(errorData.message || 'Delete failed')
      }
    } catch (err) {
      setError('Network error')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="sm:px-6 lg:px-8">
        <div className="py-6">
          <div className="max-w-7xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900">
              User Management
            </h1>
            <div className="mt-4 flex justify-between items-center">
              <button
                onClick={() => {
                  setShowAddUser(true)
                  setEditingUser(null)
                  setFormData({
                    username: '',
                    email: '',
                    password: '',
                    is_admin: false,
                    site_id: ''
                  })
                }}
                className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700"
              >
                Add User
              </button>
              {error && (
                <div className="mt-2 px-3 py-1 bg-red-50 border-l-4 border-red-400 text-red-700 text-sm">
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* User List */}
      <div className="mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {loading ? (
            <div className="h-96 flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
          ) : (
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:px-6">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Username
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Email
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Role
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Site
                        </th>
                        <th scope="col" className="relative px-6 py-3">
                          <span className="sr-only">Edit</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {users.length > 0 ? (
                        users.map((user) => (
                          <tr key={user.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {user.username}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {user.email}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {user.is_admin ? 'Admin' : 'User'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {/* Find site name - we'd need to fetch site details or include it in user data */}
                              {/* For now, show site_id or "Unknown" */}
                              {user.site_id ? `Site #${user.site_id}` : 'No site'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <button
                                onClick={() => {
                                  setShowEditUser(true)
                                  setEditingUser(user)
                                  setFormData({
                                    username: user.username,
                                    email: user.email,
                                    password: '', // Don't pre-fill password for security
                                    is_admin: user.is_admin,
                                    site_id: user.site_id || ''
                                  })
                                }}
                                className="text-indigo-600 hover:text-indigo-500"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDelete(user.id)}
                                className="ml-4 text-red-600 hover:text-red-500"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td className="px-6 py-4 text-center text-gray-500" colSpan="5">
                            No users found
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add/Edit User Modal */}
      {showAddUser || showEditUser ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900 bg-opacity-50">
          <div className="w-full max-w-md bg-white rounded-lg shadow-xl overflow-hidden">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg font-medium text-gray-900">
                {editingUser ? 'Edit User' : 'Add New User'}
              </h3>
              <button
                onClick={() => {
                  setShowAddUser(false)
                  setShowEditUser(false)
                  setEditingUser(null)
                }}
                className="mt-1 float-right text-indigo-600 hover:text-indigo-500"
              >
                ×
              </button>
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
                    value={formData.username || ''}
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
                    value={formData.email || ''}
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
                    required={!editingUser}
                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                    value={formData.password || ''}
                    onChange={handleChange}
                    placeholder={editingUser ? 'Leave blank to keep current password' : 'Password'}
                  />
                </div>
                <div className="flex items-start">
                  <div className="flex items-center h-5">
                    <input
                      id="is_admin"
                      name="is_admin"
                      type="checkbox"
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      checked={formData.is_admin || false}
                      onChange={handleChange}
                    />
                  </div>
                  <div className="ml-3 text-sm">
                    <label htmlFor="is_admin" className="font-medium text-gray-700">
                      Is Administrator
                    </label>
                  </div>
                </div>
                <div>
                  <label htmlFor="site_id" className="sr-only">Site</label>
                  <select
                    id="site_id"
                    name="site_id"
                    className="appearance-none block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                    value={formData.site_id || ''}
                    onChange={handleChange}
                  >
                    <option value="">Select a site (optional)</option>
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
                  {loading ? (editingUser ? 'Updating...' : 'Creating...') : (editingUser ? 'Update User' : 'Create User')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddUser(false)
                    setShowEditUser(false)
                    setEditingUser(null)
                  }}
                  className="mt-3 w-full flex justify-center py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}