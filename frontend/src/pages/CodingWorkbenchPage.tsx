import { useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  useCodingQueueItem,
  useAssignQueueItem,
  useCompleteQueueItem,
  useRefreshSnapshot,
  useSaveCodingResults,
} from '../hooks/useCodingQueue'
import { SplitPane, DocumentViewer, CodingPanel, CodingData } from '../components/coding'
import { TenantSwitcher } from '../components/TenantSwitcher'

export default function CodingWorkbenchPage() {
  const { queueItemId } = useParams<{ queueItemId: string }>()
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

  const { data: queueItem, isLoading, error } = useCodingQueueItem(queueItemId)
  const assignMutation = useAssignQueueItem()
  const completeMutation = useCompleteQueueItem()
  const refreshMutation = useRefreshSnapshot()
  const saveCodingMutation = useSaveCodingResults()

  // Auto-assign if not assigned
  useEffect(() => {
    if (queueItem && queueItem.status === 'pending' && !assignMutation.isPending) {
      assignMutation.mutate({ itemId: queueItem.id })
    }
  }, [queueItem?.id, queueItem?.status])

  const handleComplete = () => {
    if (queueItem) {
      completeMutation.mutate(queueItem.id, {
        onSuccess: () => {
          navigate('/code')
        },
      })
    }
  }

  const handleRefreshSnapshot = () => {
    if (queueItem) {
      refreshMutation.mutate(queueItem.id)
    }
  }

  const handleSaveCodes = (codes: CodingData) => {
    if (!queueItem) return

    const request = {
      diagnosis_codes: codes.diagnoses.map((d) => ({
        code: d.code,
        description: d.description,
        is_principal: d.isPrincipal,
        poa_indicator: d.poaIndicator,
        sequence: d.sequence,
      })),
      procedure_codes: codes.procedures.map((p) => ({
        code: p.code,
        description: p.description,
        code_type: p.codeType,
        is_principal: p.isPrincipal,
        sequence: p.sequence,
        procedure_date: p.procedureDate,
      })),
    }

    saveCodingMutation.mutate({ itemId: queueItem.id, request })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner />
          <p className="mt-4 text-gray-600">Loading coding workbench...</p>
        </div>
      </div>
    )
  }

  if (error || !queueItem) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-lg mb-4">Failed to load queue item</div>
          <Link to="/code" className="text-blue-600 hover:text-blue-700">
            Back to Queue
          </Link>
        </div>
      </div>
    )
  }

  if (!queueItem.snapshot) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-yellow-600 text-lg mb-4">No snapshot available for this item</div>
          <button
            onClick={handleRefreshSnapshot}
            disabled={refreshMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            {refreshMutation.isPending ? 'Creating Snapshot...' : 'Create Snapshot'}
          </button>
          <div className="mt-4">
            <Link to="/code" className="text-blue-600 hover:text-blue-700">
              Back to Queue
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const patientName = `${queueItem.snapshot.patient.name_family || ''}, ${queueItem.snapshot.patient.name_given || ''}`.trim()

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 flex-shrink-0">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Left side - Navigation and patient info */}
            <div className="flex items-center gap-4">
              <Link
                to="/code"
                className="flex items-center gap-1 text-gray-500 hover:text-gray-700"
              >
                <ArrowLeftIcon className="w-5 h-5" />
                <span className="text-sm">Queue</span>
              </Link>
              <div className="border-l border-gray-300 h-6" />
              <div>
                <h1 className="text-lg font-semibold text-gray-900">{patientName}</h1>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <span>MRN: {queueItem.snapshot.patient.mrn || 'N/A'}</span>
                  <span>|</span>
                  <span>Visit: {queueItem.snapshot.encounter.visit_number || 'N/A'}</span>
                  <span>|</span>
                  <span>Type: {queueItem.snapshot.encounter.encounter_type || 'N/A'}</span>
                </div>
              </div>
            </div>

            {/* Right side - Actions and user info */}
            <div className="flex items-center gap-4">
              {/* Billing component badge */}
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  queueItem.billing_component === 'facility'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-purple-100 text-purple-700'
                }`}
              >
                {queueItem.billing_component === 'facility' ? 'Facility' : 'Professional'}
              </span>

              {/* Status badge */}
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${
                  queueItem.status === 'in_progress'
                    ? 'bg-yellow-100 text-yellow-700'
                    : queueItem.status === 'completed'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-700'
                }`}
              >
                {queueItem.status}
              </span>

              {/* Refresh snapshot button */}
              <button
                onClick={handleRefreshSnapshot}
                disabled={refreshMutation.isPending}
                className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50"
                title="Refresh snapshot with latest data"
              >
                <RefreshIcon
                  className={`w-5 h-5 ${refreshMutation.isPending ? 'animate-spin' : ''}`}
                />
              </button>

              {/* Complete button */}
              <button
                onClick={handleComplete}
                disabled={completeMutation.isPending}
                className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:bg-gray-400"
              >
                {completeMutation.isPending ? 'Completing...' : 'Complete Coding'}
              </button>

              <div className="border-l border-gray-300 h-6" />

              <TenantSwitcher
                currentTenant={currentTenant}
                availableTenants={availableTenants}
                onSwitchTenant={switchTenant}
                isSwitching={isSwitchingTenant}
                isImpersonating={isImpersonating}
                onStopImpersonation={stopImpersonation}
              />
              <span className="text-sm text-gray-600">{user?.full_name}</span>
              <button
                onClick={logout}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>

        {/* Snapshot version info */}
        {queueItem.snapshot_version && (
          <div className="px-4 py-1 bg-gray-50 border-t border-gray-100 text-xs text-gray-500">
            Snapshot v{queueItem.snapshot_version} | Created:{' '}
            {new Date(queueItem.snapshot.snapshot_created_at).toLocaleString()}
          </div>
        )}
      </header>

      {/* Main content - Split pane */}
      <main className="flex-1 overflow-hidden">
        <SplitPane
          left={<DocumentViewer snapshot={queueItem.snapshot} />}
          right={
            <CodingPanel
              billingComponent={queueItem.billing_component}
              onSave={handleSaveCodes}
              isSaving={saveCodingMutation.isPending}
            />
          }
          defaultLeftWidth={50}
          minLeftWidth={30}
          maxLeftWidth={70}
        />
      </main>
    </div>
  )
}

function LoadingSpinner() {
  return (
    <svg
      className="animate-spin h-8 w-8 text-blue-600 mx-auto"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

function ArrowLeftIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10 19l-7-7m0 0l7-7m-7 7h18"
      />
    </svg>
  )
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      />
    </svg>
  )
}
