import { CodeSearchInput } from './CodeSearchInput'

export interface DiagnosisCode {
  id: string
  code: string
  description: string
  isPrincipal: boolean
  poaIndicator: string | null // Y, N, U, W, or 1 (exempt)
  sequence: number
}

const POA_OPTIONS = [
  { value: 'Y', label: 'Y - Yes, present on admission' },
  { value: 'N', label: 'N - No, developed during stay' },
  { value: 'U', label: 'U - Unknown' },
  { value: 'W', label: 'W - Clinically undetermined' },
  { value: '1', label: 'Exempt' },
]

interface DiagnosisEntryProps {
  codes: DiagnosisCode[]
  onChange: (codes: DiagnosisCode[]) => void
}

export function DiagnosisEntry({ codes, onChange }: DiagnosisEntryProps) {
  const principalDiagnosis = codes.find((c) => c.isPrincipal)
  const secondaryDiagnoses = codes.filter((c) => !c.isPrincipal)

  const handleAddCode = (code: { code: string; description: string }, isPrincipal: boolean) => {
    const newCode: DiagnosisCode = {
      id: crypto.randomUUID(),
      code: code.code,
      description: code.description,
      isPrincipal,
      poaIndicator: 'Y',
      sequence: isPrincipal ? 1 : codes.length + 1,
    }

    if (isPrincipal) {
      // Replace principal or demote existing
      const updated = codes.map((c) =>
        c.isPrincipal ? { ...c, isPrincipal: false, sequence: codes.length + 1 } : c
      )
      onChange([newCode, ...updated])
    } else {
      onChange([...codes, newCode])
    }
  }

  const handleRemoveCode = (id: string) => {
    const updated = codes.filter((c) => c.id !== id)
    // Resequence
    const resequenced = updated.map((c, i) => ({
      ...c,
      sequence: c.isPrincipal ? 1 : i + 1,
    }))
    onChange(resequenced)
  }

  const handleUpdatePOA = (id: string, poa: string) => {
    const updated = codes.map((c) => (c.id === id ? { ...c, poaIndicator: poa } : c))
    onChange(updated)
  }

  const handleMakePrincipal = (id: string) => {
    const updated = codes.map((c) => ({
      ...c,
      isPrincipal: c.id === id,
      sequence: c.id === id ? 1 : c.sequence,
    }))
    // Resequence non-principal
    const resequenced = updated.map((c, i) => ({
      ...c,
      sequence: c.isPrincipal ? 1 : i + 1,
    }))
    onChange(resequenced)
  }

  return (
    <div className="space-y-4">
      {/* Principal Diagnosis */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Principal Diagnosis</label>
        {principalDiagnosis ? (
          <DiagnosisCodeCard
            diagnosis={principalDiagnosis}
            onRemove={() => handleRemoveCode(principalDiagnosis.id)}
            onUpdatePOA={(poa) => handleUpdatePOA(principalDiagnosis.id, poa)}
            isPrincipal
          />
        ) : (
          <CodeSearchInput
            codeType="ICD-10-CM"
            onSelect={(code) => handleAddCode(code, true)}
            placeholder="Search for principal diagnosis..."
          />
        )}
      </div>

      {/* Secondary Diagnoses */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Secondary Diagnoses</label>
        <div className="space-y-2">
          {secondaryDiagnoses.map((diagnosis) => (
            <DiagnosisCodeCard
              key={diagnosis.id}
              diagnosis={diagnosis}
              onRemove={() => handleRemoveCode(diagnosis.id)}
              onUpdatePOA={(poa) => handleUpdatePOA(diagnosis.id, poa)}
              onMakePrincipal={() => handleMakePrincipal(diagnosis.id)}
            />
          ))}
        </div>
        <div className="mt-2">
          <CodeSearchInput
            codeType="ICD-10-CM"
            onSelect={(code) => handleAddCode(code, false)}
            placeholder="Add secondary diagnosis..."
          />
        </div>
      </div>
    </div>
  )
}

interface DiagnosisCodeCardProps {
  diagnosis: DiagnosisCode
  onRemove: () => void
  onUpdatePOA: (poa: string) => void
  onMakePrincipal?: () => void
  isPrincipal?: boolean
}

function DiagnosisCodeCard({
  diagnosis,
  onRemove,
  onUpdatePOA,
  onMakePrincipal,
  isPrincipal,
}: DiagnosisCodeCardProps) {
  return (
    <div
      className={`border rounded-md p-3 ${
        isPrincipal ? 'border-blue-300 bg-blue-50' : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-medium text-blue-600">{diagnosis.code}</span>
            {isPrincipal && (
              <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                Principal
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 mt-1 truncate">{diagnosis.description}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* POA Selector */}
          <select
            value={diagnosis.poaIndicator || 'Y'}
            onChange={(e) => onUpdatePOA(e.target.value)}
            className="text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {POA_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                POA: {opt.value}
              </option>
            ))}
          </select>
          {/* Make Principal button */}
          {!isPrincipal && onMakePrincipal && (
            <button
              onClick={onMakePrincipal}
              className="text-xs text-blue-600 hover:text-blue-700"
              title="Make principal"
            >
              <ArrowUpIcon className="w-4 h-4" />
            </button>
          )}
          {/* Remove button */}
          <button
            onClick={onRemove}
            className="text-gray-400 hover:text-red-500"
            title="Remove"
          >
            <XIcon className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

function ArrowUpIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
    </svg>
  )
}
