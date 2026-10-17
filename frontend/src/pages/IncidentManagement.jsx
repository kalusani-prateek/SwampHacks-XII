import React, { useState, useEffect } from 'react'

export default function IncidentManagement() {
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAddIncident, setShowAddIncident] = useState(false)
  const [showEditIncident, setShowEditIncident] = useState(false)
  const [editingIncident, setEditingIncident] = useState(null)
  const [formData, setFormData] = useState({
    image: '',
    location: '',
    description: '',
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

  // Fetch incidents
  useEffect(() => {
    const fetchIncidents = async () => {
      try {
        const res = await fetch('/api/incidents/get_incidents')
        if (res.ok) {
          const data = await res.json()
          setIncidents(Array.isArray(data) ? data : [])
        } else {
          throw new Error('Failed to fetch incidents')
        }
      } catch (err) {
        setError('Failed to load incidents')
      } finally {
        setLoading(false)
      }
    }

    fetchIncidents()
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
      if (editingIncident) {
        // Update incident
        res = await fetch(`/api/incidents/${editingIncident.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify(formData)
        })
      } else {
        // Add incident
        res = await fetch('/api/incidents/add_incident', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify(formData)
        })
      }

      if (res.ok) {
        // Refresh incidents list
        const incidentsRes = await fetch('/api/incidents/get_incidents')
        if (incidentsRes.ok) {
          const incidentsData = await incidentsRes.json()
          setIncidents(Array.isArray(incidentsData) ? incidentsData : [])
        }
        setShowAddIncident(false)
        setShowEditIncident(false)
        setEditingIncident(null)
        setFormData({
          image: '',
          location: '',
          description: '',
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

  const handleDelete = async (incidentId) => {
    if (!window.confirm('Are you sure you want to delete this incident?')) {
      return
    }

    try {
      const res = await fetch(`/api/incidents/${incidentId}`, {
        method: 'DELETE',
        credentials: 'include'
      })
      if (res.ok) {
        // Refresh incidents list
        const incidentsRes = await fetch('/api/incidents/get_incidents')
        if (incidentsRes.ok) {
          const incidentsData = await incidentsRes.json()
          setIncidents(Array.isArray(incidentsData) ? incidentsData : [])
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
              Incident Management
            </h1>
            <div className="mt-4 flex justify-between items-center">
              <button
                onClick={() => {
                  setShowAddIncident(true)
                  setEditingIncident(null)
                  setFormData({
                    image: '',
                    location: '',
                    description: '',
                    site_id: ''
                  })
                }}
                className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700"
              >
                Report Incident
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

      {/* Incidents List */}
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
                          Location
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Description
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Site
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th scope="col" className="relative px-6 py-3">
                          <span className="sr-only">Edit</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {incidents.length > 0 ? (
                        incidents.map((incident) => (
                          <tr key={incident.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {incident.users_username}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {incident.location}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 line-clamp-2">
                              {incident.description}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {/* Find site name - we'd need to fetch site details or include it in incident data */}
                              {/* For now, show site_id or "Unknown" */}
                              {incident.site_id ? `Site #${incident.site_id}` : 'No site'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(incident.date_posted).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <button
                                onClick={() => {
                                  setShowEditIncident(true)
                                  setEditingIncident(incident)
                                  setFormData({
                                    image: incident.image,
                                    location: incident.location,
                                    description: incident.description,
                                    site_id: incident.site_id || ''
                                  })
                                }}
                                className="text-indigo-600 hover:text-indigo-500"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDelete(incident.id)}
                                className="ml-4 text-red-600 hover:text-red-500"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td className="px-6 py-4 text-center text-gray-500" colSpan="6">
                            No incidents found
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

      {/* Add/Edit Incident Modal */}
      {(showAddIncident || showEditIncident) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900 bg-opacity-50">
          <div className="w-full max-w-2xl bg-white rounded-lg shadow-xl overflow-hidden">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg font-medium text-gray-900">
                {editingIncident ? 'Edit Incident' : 'Report New Incident'}
              </h3>
              <button
                onClick={() => {
                  setShowAddIncident(false)
                  setShowEditIncident(false)
                  setEditingIncident(null)
                }}
                className="mt-1 float-right text-indigo-600 hover:text-indigo-500"
              >
                ×
              </button>
            </div>
            <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
              <div className="rounded-md shadow-sm -space-y-px">
                <div>
                  <label htmlFor="image" className="sr-only">Image URL</label>
                  <input
                    id="image"
                    name="image"
                    type="text"
                    required
                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                    value={formData.image || ''}
                    onChange={handleChange}
                    placeholder="Image URL (or base64)"
                  />
                </div>
                <div>
                  <label htmlFor="location" className="sr-only">Location</label>
                  <input
                    id="location"
                    name="location"
                    type="text"
                    required
                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                    value={formData.location || ''}
                    onChange={handleChange}
                    placeholder="Location"
                  />
                </div>
                <div>
                  <label htmlFor="description" className="sr-only">Description</label>
                  <textarea
                    id="description"
                    name="description"
                    rows="4"
                    required
                    className="block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                    value={formData.description || ''}
                    onChange={handleChange}
                    placeholder="Description"
                  />
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
                  {loading ? (editingIncident ? 'Updating...' : 'Creating...') : (editingIncident ? 'Update Incident' : 'Report Incident')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddIncident(false)
                    setShowEditIncident(false)
                    setEditingIncident(null)
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