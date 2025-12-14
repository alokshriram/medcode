import { useAuth } from '../hooks/useAuth'
import { useDashboard } from '../hooks/useDashboard'

export default function DashboardPage() {
  const { user, logout } = useAuth()
  const { data: dashboard, isLoading } = useDashboard()

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-900">MedCode</h1>
          <div className="flex items-center gap-4">
            <span className="text-gray-600">{user?.full_name}</span>
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-semibold text-gray-900 mb-6">Dashboard</h2>

        {isLoading ? (
          <p>Loading dashboard...</p>
        ) : dashboard ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <DashboardCard
              title="Pending Tasks"
              value={dashboard.pending_tasks}
              color="yellow"
            />
            <DashboardCard
              title="In Progress"
              value={dashboard.in_progress_tasks}
              color="blue"
            />
            <DashboardCard
              title="Completed Today"
              value={dashboard.completed_tasks_today}
              color="green"
            />
            <DashboardCard
              title="Total Records"
              value={dashboard.total_records}
              color="gray"
            />
          </div>
        ) : null}
      </main>
    </div>
  )
}

function DashboardCard({
  title,
  value,
  color,
}: {
  title: string
  value: number
  color: 'yellow' | 'blue' | 'green' | 'gray'
}) {
  const colorClasses = {
    yellow: 'bg-yellow-50 border-yellow-200',
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    gray: 'bg-gray-50 border-gray-200',
  }

  return (
    <div className={`p-6 rounded-lg border ${colorClasses[color]}`}>
      <p className="text-sm text-gray-600">{title}</p>
      <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
    </div>
  )
}
