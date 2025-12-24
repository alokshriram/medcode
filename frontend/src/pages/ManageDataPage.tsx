import { useAuth } from '../hooks/useAuth'
import { Navigate, Link } from 'react-router-dom'
import { ManageDataPanel } from '../components/ManageDataPanel'

export default function ManageDataPage() {
  const { user, logout } = useAuth()

  // Role gate - redirect if no access
  const hasAccess = user?.roles?.some((role) => ['coder', 'admin'].includes(role.toLowerCase()))

  if (!hasAccess) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-gray-500 hover:text-gray-700">
              <ArrowLeftIcon />
            </Link>
            <h1 className="text-xl font-bold text-gray-900">Manage Data</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-gray-600">{user?.full_name}</span>
            <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">
              Sign out
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <ManageDataPanel userRoles={user?.roles || []} />
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
