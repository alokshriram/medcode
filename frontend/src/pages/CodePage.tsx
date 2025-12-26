import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useEncounters } from '../hooks/useEncounters'
import { TenantSwitcher } from '../components/TenantSwitcher'

export default function CodePage() {
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
  const { data: encountersData, isLoading, error } = useEncounters()

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-gray-500 hover:text-gray-700">
              <ArrowLeftIcon />
            </Link>
            <h1 className="text-xl font-bold text-gray-900">Code</h1>
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
        <h2 className="text-2xl font-semibold text-gray-900 mb-6">Encounters</h2>

        {isLoading && (
          <div className="text-center py-8 text-gray-500">Loading encounters...</div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-700">
            Error loading encounters. Please try again.
          </div>
        )}

        {encountersData && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    First Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Encounter ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Encounter Type
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {encountersData.encounters.map((encounter) => (
                  <tr key={encounter.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {encounter.patient.name_given || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {encounter.patient.name_family || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {encounter.visit_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {encounter.encounter_type || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {encountersData.encounters.length === 0 && (
              <div className="text-center py-8 text-gray-500">No encounters found</div>
            )}

            {encountersData.total > 0 && (
              <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
                Showing {encountersData.encounters.length} of {encountersData.total} encounters
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
