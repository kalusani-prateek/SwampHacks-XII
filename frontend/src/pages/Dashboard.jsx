import React, { useState, useEffect } from 'react'

export default function Dashboard() {
  const [stats, setStats] = useState({
    users: 0,
    sites: 0,
    incidents: 0
  })
  const [recentIncidents, setRecentIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch stats
        const [usersRes, sitesRes, incidentsRes] = await Promise.all([
          fetch('/api/users'),
          fetch('/api/sites/get_sites'),
          fetch('/api/incidents/get_incidents')
        ])

        if (usersRes.ok && sitesRes.ok && incidentsRes.ok) {
          const [usersData, sitesData, incidentsData] = await Promise.all([
            usersRes.json(),
            sitesRes.json(),
            incidentsRes.json()
          ])

          setStats({
            users: Array.isArray(usersData.users) ? usersData.users.length : 0,
            sites: Array.isArray(sitesData) ? sitesData.length : 0,
            incidents: Array.isArray(incidentsData) ? incidentsData.length : 0
          })

          // Get recent incidents (last 5)
          const sortedIncidents = [...incidentsData].sort((a, b) =>
            new Date(b.date_posted) - new Date(a.date_posted)
          ).slice(0, 5)
          setRecentIncidents(sortedIncidents)
        } else {
          throw new Error('Failed to fetch data')
        }
      } catch (err) {
        setError('Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="sm:px-6 lg:px-8">
        <div className="py-6">
          <div className="max-w-7xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900">
              Dashboard
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              Overview of your SwampHacks XII system
            </p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg font-medium text-gray-500">
                Total Users
              </h3>
              <p className="mt-1 text-3xl font-semibold text-gray-900">
                {stats.users}
              </p>
            </div>
          </div>
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg font-medium text-gray-500">
                Total Sites
              </h3>
              <p className="mt-1 text-3xl font-semibold text-gray-900">
                {stats.sites}
              </p>
            </div>
          </div>
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg font-medium text-gray-500">
                Total Incidents
              </h3>
              <p className="mt-1 text-3xl font-semibold text-gray-900">
                {stats.incidents}
              </p>
            </div>
          </div>
        </div>

        {/* Recent Incidents */}
        <div className="mt-8">
          <div className="max-w-7xl mx-auto">
            <h2 className="sr-only">Recent Incidents</h2>
            <div className="divide-y divide-gray-200">
              {recentIncidents.length > 0 ? (
                recentIncidents.map((incident) => (
                  <div key={incident.id} className="px-4 py-5 sm:px-6">
                    <div className="flex justify-between text-sm font-medium text-gray-900">
                      <div>
                        <p className="text-gray-700">{incident.location}</p>
                        <p className="text-indigo-600">{incident.users_username}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">
                          {new Date(incident.date_posted).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500 line-clamp-2">
                        {incident.description}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="px-4 py-5 sm:px-6 text-center text-gray-500">
                  No recent incidents
                </div>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-6 px-4 py-3 max-w-sm mx-auto bg-red-50 border-l-4 border-red-400 text-red-700">
            <p>{error}</p>
          </div>
        )}
      </div>
    </div>
  )
}