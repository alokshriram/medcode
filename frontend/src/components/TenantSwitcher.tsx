import { useState, useRef, useEffect } from 'react'
import { Tenant } from '../api/auth'

interface TenantSwitcherProps {
  currentTenant: Tenant | null
  availableTenants: Tenant[]
  onSwitchTenant: (tenantId: string) => void
  isSwitching: boolean
  isImpersonating?: boolean
  onStopImpersonation?: () => void
}

export function TenantSwitcher({
  currentTenant,
  availableTenants,
  onSwitchTenant,
  isSwitching,
  isImpersonating,
  onStopImpersonation,
}: TenantSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Don't render if no tenants available
  if (availableTenants.length === 0) {
    return null
  }

  // If only one tenant and not impersonating, show simple label
  if (availableTenants.length === 1 && !isImpersonating) {
    return (
      <span className="text-sm text-gray-600 px-2 py-1 bg-gray-100 rounded">
        {currentTenant?.name || 'Default'}
      </span>
    )
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isSwitching}
        className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded border transition-colors ${
          isImpersonating
            ? 'bg-amber-50 border-amber-300 text-amber-800'
            : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100'
        } ${isSwitching ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {isImpersonating && (
          <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
        )}
        <span>{currentTenant?.name || 'Select Tenant'}</span>
        <ChevronDownIcon />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1 w-56 bg-white rounded-md shadow-lg border border-gray-200 z-50">
          <div className="py-1">
            {availableTenants.map((tenant) => (
              <button
                key={tenant.id}
                onClick={() => {
                  if (tenant.id !== currentTenant?.id) {
                    onSwitchTenant(tenant.id)
                  }
                  setIsOpen(false)
                }}
                disabled={isSwitching}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center justify-between ${
                  tenant.id === currentTenant?.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                }`}
              >
                <span>{tenant.name}</span>
                {tenant.id === currentTenant?.id && <CheckIcon />}
              </button>
            ))}

            {isImpersonating && onStopImpersonation && (
              <>
                <div className="border-t border-gray-100 my-1" />
                <button
                  onClick={() => {
                    onStopImpersonation()
                    setIsOpen(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-amber-700 hover:bg-amber-50 flex items-center gap-2"
                >
                  <ExitIcon />
                  <span>Stop Impersonating</span>
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function ChevronDownIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}

function ExitIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
    </svg>
  )
}
