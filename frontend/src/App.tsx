import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ManageDataPage from './pages/ManageDataPage'
import CodePage from './pages/CodePage'
import CodingWorkbenchPage from './pages/CodingWorkbenchPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/manage-data"
        element={
          <ProtectedRoute>
            <ManageDataPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/code"
        element={
          <ProtectedRoute>
            <CodePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/code/:queueItemId"
        element={
          <ProtectedRoute>
            <CodingWorkbenchPage />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default App
