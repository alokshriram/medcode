import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useCodingQueue } from '../hooks/useCodingQueue'
import { TenantSwitcher } from '../components/TenantSwitcher'
import { ListQueueParams } from '../api/codingQueue'

export default function CodePage() {
  const navigate = useNavigate()
  const {
    user,
    logout,
    currentTenant,
    availableTenants,
    switchTenant,
    isSwitchingTenant,
    isImpersonating,
    stopImpersonation,
  } = useAuth()

  // Filter state
  const [filters, setFilters] = useState<ListQueueParams>({
    limit: 50,
  })

  const { data: queueData, isLoading, error } = useCodingQueue(filters)

  const handleRowClick = (itemId: string) => {
    navigate(`/code/${itemId}`)
  }

  const handleFilterChange = (key: keyof ListQueueParams, value: string | boolean | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === '' ? undefined : value,
    }))
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-gray-500 hover:text-gray-700">
              <ArrowLeftIcon />
            </Link>
            <h1 className="text-xl font-bold text-gray-900">Coding Queue</h1>
          </div>
          <div className="flex items-center gap-4">
            <TenantSwitcher
              currentTenant={currentTenant}
              availableTenants={availableTenants}
              onSwitchTenant={switchTenant}
              isSwitching={isSwitchingTenant}
              isImpersonating={isImpersonating}
              onStopImpersonation={stopImpersonation}
            />
            <span className="text-gray-600">{user?.full_name}</span>
            <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">
              Sign out
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Filters */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-end">
            {/* Status filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filters.status || ''}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            {/* Billing component filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Billing Component
              </label>
              <select
                value={filters.billing_component || ''}
                onChange={(e) =>
                  handleFilterChange(
                    'billing_component',
                    e.target.value as 'facility' | 'professional' | undefined
                  )
                }
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="facility">Facility</option>
                <option value="professional">Professional</option>
              </select>
            </div>

            {/* Assigned to me toggle */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="assignedToMe"
                checked={filters.assigned_to_me || false}
                onChange={(e) => handleFilterChange('assigned_to_me', e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="assignedToMe" className="text-sm text-gray-700">
                Assigned to me
              </label>
            </div>

            {/* Clear filters */}
            <button
              onClick={() => setFilters({ limit: 50 })}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear filters
            </button>
          </div>
        </div>

        <h2 className="text-2xl font-semibold text-gray-900 mb-6">Work Items</h2>

        {isLoading && (
          <div className="text-center py-8 text-gray-500">Loading queue items...</div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-700">
            Error loading queue. Please try again.
          </div>
        )}

        {queueData && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Patient
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Visit #
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Billing
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Priority
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {queueData.items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => handleRowClick(item.id)}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {item.patient_name || 'Unknown'}
                      </div>
                      <div className="text-xs text-gray-500">MRN: {item.patient_mrn || 'N/A'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {item.visit_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {item.encounter_type || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded-full ${
                          item.billing_component === 'facility'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-purple-100 text-purple-700'
                        }`}
                      >
                        {item.billing_component === 'facility' ? 'Facility' : 'Professional'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          item.status === 'pending'
                            ? 'bg-gray-100 text-gray-700'
                            : item.status === 'in_progress'
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-green-100 text-green-700'
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {item.priority > 0 ? (
                        <span className="flex items-center gap-1 text-sm">
                          <PriorityIcon className="w-4 h-4 text-red-500" />
                          {item.priority}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">Normal</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {queueData.items.length === 0 && (
              <div className="text-center py-8 text-gray-500">No queue items found</div>
            )}

            {queueData.total > 0 && (
              <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
                Showing {queueData.items.length} of {queueData.total} items
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

function ArrowLeftIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
    </svg>
  )
}

function PriorityIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 20 20">
      <path
        fillRule="evenodd"
        d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
        clipRule="evenodd"
      />
    </svg>
  )
}
