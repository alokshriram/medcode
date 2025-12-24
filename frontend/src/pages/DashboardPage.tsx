import { useAuth } from '../hooks/useAuth'
import { DashboardTile } from '../components/DashboardTile'

export default function DashboardPage() {
  const { user, logout } = useAuth()

  // Check if user has coder/admin role for Manage Data
  const hasManageDataAccess = user?.roles?.some((role) =>
    ['coder', 'admin'].includes(role.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-900">MedCode</h1>
          <div className="flex items-center gap-4">
            <span className="text-gray-600">{user?.full_name}</span>
            <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">
              Sign out
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-semibold text-gray-900 mb-6">Dashboard</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <DashboardTile
            title="Manage Data"
            description="Upload HL7 files to import patient encounters"
            to="/manage-data"
            icon={<UploadIcon />}
            disabled={!hasManageDataAccess}
          />
          <DashboardTile
            title="Code"
            description="View and process patient encounters"
            to="/code"
            icon={<CodeIcon />}
          />
        </div>
      </main>
    </div>
  )
}

function UploadIcon() {
  return (
    <svg
      className="h-12 w-12"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
      />
    </svg>
  )
}

function CodeIcon() {
  return (
    <svg
      className="h-12 w-12"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  )
}
