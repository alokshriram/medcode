import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../hooks/useAuth'

export default function LoginPage() {
  const navigate = useNavigate()
  const { isAuthenticated, login, loginError, isLoggingIn } = useAuth()

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard')
    }
  }, [isAuthenticated, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h1 className="text-3xl font-bold text-center text-gray-900">MedCode</h1>
          <p className="mt-2 text-center text-gray-600">Medical Coding Workflow Tool</p>
        </div>

        <div className="mt-8 flex justify-center">
          {isLoggingIn ? (
            <p>Signing in...</p>
          ) : (
            <GoogleLogin
              onSuccess={(credentialResponse) => {
                if (credentialResponse.credential) {
                  login(credentialResponse.credential)
                }
              }}
              onError={() => {
                console.error('Google login failed')
              }}
            />
          )}
        </div>

        {loginError && (
          <p className="text-red-500 text-center text-sm">
            Failed to sign in. Please try again.
          </p>
        )}
      </div>
    </div>
  )
}
