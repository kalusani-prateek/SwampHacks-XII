import React, { useState, useEffect } from 'react'

export default function SiteManagement() {
  const [sites, setSites] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAddSite, setShowAddSite] = useState(false)
  const [showEditSite, setShowEditSite] = useState(false)
  const [editingSite, setEditingSite] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    city: '',
    state: ''
  })

  // Fetch sites
  useEffect(() => {
    const fetchSites = async () => {
      try {
        const res = await fetch('/api/sites/get_sites')
        if (res.ok) {
          const data = await res.json()
          setSites(Array.isArray(data) ? data : [])
        } else {
          throw new Error('Failed to fetch sites')
        }
      } catch (err) {
        setError('Failed to load sites')
      } finally {
        setLoading(false)
      }
    }

    fetchSites()
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

    try {
      let res
      if (editingSite) {
        // Update site
        res = await fetch(`/api/sites/${editingSite.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify(formData)
        })
      } else {
        // Add site
        res = await fetch('/api/sites/add_site', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify(formData)
        })
      }

      if (res.ok) {
        // Refresh sites list
        const sitesRes = await fetch('/api/sites/get_sites')
        if (sitesRes.ok) {
          const sitesData = await sitesRes.json()
          setSites(Array.isArray(sitesData) ? sitesData : [])
        }
        setShowAddSite(false)
        setShowEditSite(false)
        setEditingSite(null)
        setFormData({
          name: '',
          city: '',
          state: ''
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

  const handleDelete = async (siteId) => {
    if (!window.confirm('Are you sure you want to delete this site?')) {
      return
    }

    try {
      const res = await fetch(`/api/sites/${siteId}`, {
        method: 'DELETE',
        credentials: 'include'
      })
      if (res.ok) {
        // Refresh sites list
        const sitesRes = await fetch('/api/sites/get_sites')
        if (sitesRes.ok) {
          const sitesData = await sitesRes.json()
          setSites(Array.isArray(sitesData) ? sitesData : [])
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
              Site Management
            </h1>
            <div className="mt-4 flex justify-between items-center">
              <button
                onClick={() => {
                  setShowAddSite(true)
                  setEditingSite(null)
                  setFormData({
                    name: '',
                    city: '',
                    state: ''
                  })
                }}
                className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700"
              >
                Add Site
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

      {/* Sites List */}
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
                          Name
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          City
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          State
                        </th>
                        <th scope="col" className="relative px-6 py-3">
                          <span className="sr-only">Edit</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {sites.length > 0 ? (
                        sites.map((site) => (
                          <tr key={site.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {site.name}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {site.city}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {site.state}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <button
                                onClick={() => {
                                  setShowEditSite(true)
                                  setEditingSite(site)
                                  setFormData({
                                    name: site.name,
                                    city: site.city,
                                    state: site.state
                                  })
                                }}
                                className="text-indigo-600 hover:text-indigo-500"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDelete(site.id)}
                                className="ml-4 text-red-600 hover:text-red-500"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td className="px-6 py-4 text-center text-gray-500" colSpan="4">
                            No sites found
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

      {/* Add/Edit Site Modal */}
      {(showAddSite || showEditSite) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900 bg-opacity-50">
          <div className="w-full max-w-md bg-white rounded-lg shadow-xl overflow-hidden">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg font-medium text-gray-900">
                {editingSite ? 'Edit Site' : 'Add New Site'}
              </h3>
              <button
                onClick={() => {
                  setShowAddSite(false)
                  setShowEditSite(false)
                  setEditingSite(null)
                }}
                className="mt-1 float-right text-indigo-600 hover:text-indigo-500"
              >
                ×
              </button>
            </div>
            <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
              <div className="rounded-md shadow-sm -space-y-px">
                <div>
                  <label htmlFor="name" className="sr-only">Name</label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    required
                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                    value={formData.name || ''}
                    onChange={handleChange}
                    placeholder="Site Name"
                  />
                </div>
                <div>
                  <label htmlFor="city" className="sr-only">City</label>
                  <input
                    id="city"
                    name="city"
                    type="text"
                    required
                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                    value={formData.city || ''}
                    onChange={handleChange}
                    placeholder="City"
                  />
                </div>
                <div>
                  <label htmlFor="state" className="sr-only">State</label>
                  <input
                    id="state"
                    name="state"
                    type="text"
                    required
                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                    value={formData.state || ''}
                    onChange={handleChange}
                    placeholder="State"
                  />
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={loading}
                  className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  {loading ? (editingSite ? 'Updating...' : 'Creating...') : (editingSite ? 'Update Site' : 'Create Site')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddSite(false)
                    setShowEditSite(false)
                    setEditingSite(null)
                  }}
                  className="mt-3 w-full flex justify-center py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}