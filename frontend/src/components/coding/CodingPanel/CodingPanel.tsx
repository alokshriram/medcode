import { useState } from 'react'
import { DiagnosisEntry, DiagnosisCode } from './DiagnosisEntry'
import { ProcedureEntry, ProcedureCode } from './ProcedureEntry'

export interface CodingData {
  diagnoses: DiagnosisCode[]
  procedures: ProcedureCode[]
}

interface CodingPanelProps {
  billingComponent: 'facility' | 'professional'
  initialDiagnoses?: DiagnosisCode[]
  initialProcedures?: ProcedureCode[]
  onSave?: (codes: CodingData) => void
  isSaving?: boolean
}

export function CodingPanel({
  billingComponent,
  initialDiagnoses = [],
  initialProcedures = [],
  onSave,
  isSaving,
}: CodingPanelProps) {
  const [diagnoses, setDiagnoses] = useState<DiagnosisCode[]>(initialDiagnoses)
  const [procedures, setProcedures] = useState<ProcedureCode[]>(initialProcedures)

  // Determine procedure code type based on billing component
  const procedureCodeType = billingComponent === 'facility' ? 'ICD-10-PCS' : 'CPT'

  const handleSave = () => {
    if (onSave) {
      onSave({ diagnoses, procedures })
    }
  }

  const totalCodes = diagnoses.length + procedures.length

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {billingComponent === 'facility' ? 'Facility' : 'Professional'} Coding
            </h2>
            <p className="text-sm text-gray-500">
              {totalCodes} code{totalCodes !== 1 ? 's' : ''} entered
            </p>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              billingComponent === 'facility'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-purple-100 text-purple-700'
            }`}
          >
            {billingComponent === 'facility' ? 'ICD-10-PCS' : 'CPT'}
          </span>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Diagnosis Section */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <DiagnosisIcon className="w-5 h-5 text-blue-600" />
            <h3 className="text-md font-medium text-gray-900">Diagnosis Codes (ICD-10-CM)</h3>
          </div>
          <DiagnosisEntry codes={diagnoses} onChange={setDiagnoses} />
        </section>

        {/* Divider */}
        <hr className="border-gray-200" />

        {/* Procedure Section */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <ProcedureIcon className="w-5 h-5 text-purple-600" />
            <h3 className="text-md font-medium text-gray-900">
              Procedure Codes ({procedureCodeType})
            </h3>
          </div>
          <ProcedureEntry
            codes={procedures}
            onChange={setProcedures}
            codeType={procedureCodeType}
          />
        </section>
      </div>

      {/* Footer with save button */}
      {onSave && (
        <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">
              {diagnoses.length} diagnosis, {procedures.length} procedure codes
            </div>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                isSaving
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {isSaving ? 'Saving...' : 'Save Codes'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function DiagnosisIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}

function ProcedureIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z" />
    </svg>
  )
}
