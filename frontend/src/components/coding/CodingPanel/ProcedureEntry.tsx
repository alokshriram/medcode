import { CodeSearchInput, CodeType } from './CodeSearchInput'

export interface ProcedureCode {
  id: string
  code: string
  description: string
  codeType: 'ICD-10-PCS' | 'CPT'
  isPrincipal: boolean
  sequence: number
  procedureDate: string | null
}

interface ProcedureEntryProps {
  codes: ProcedureCode[]
  onChange: (codes: ProcedureCode[]) => void
  codeType: 'ICD-10-PCS' | 'CPT'
}

export function ProcedureEntry({ codes, onChange, codeType }: ProcedureEntryProps) {
  const principalProcedure = codes.find((c) => c.isPrincipal)
  const secondaryProcedures = codes.filter((c) => !c.isPrincipal)

  const handleAddCode = (code: { code: string; description: string }, isPrincipal: boolean) => {
    const newCode: ProcedureCode = {
      id: crypto.randomUUID(),
      code: code.code,
      description: code.description,
      codeType,
      isPrincipal,
      sequence: isPrincipal ? 1 : codes.length + 1,
      procedureDate: null,
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

  const handleUpdateDate = (id: string, date: string) => {
    const updated = codes.map((c) => (c.id === id ? { ...c, procedureDate: date || null } : c))
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

  const codeTypeLabel = codeType === 'ICD-10-PCS' ? 'ICD-10-PCS' : 'CPT'
  const searchCodeType: CodeType = codeType === 'CPT' ? 'CPT' : 'ICD-10-PCS'

  return (
    <div className="space-y-4">
      {/* Principal Procedure */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Principal Procedure ({codeTypeLabel})
        </label>
        {principalProcedure ? (
          <ProcedureCodeCard
            procedure={principalProcedure}
            onRemove={() => handleRemoveCode(principalProcedure.id)}
            onUpdateDate={(date) => handleUpdateDate(principalProcedure.id, date)}
            isPrincipal
          />
        ) : (
          <CodeSearchInput
            codeType={searchCodeType}
            onSelect={(code) => handleAddCode(code, true)}
            placeholder={`Search for principal ${codeTypeLabel} procedure...`}
          />
        )}
      </div>

      {/* Secondary Procedures */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Secondary Procedures
        </label>
        <div className="space-y-2">
          {secondaryProcedures.map((procedure) => (
            <ProcedureCodeCard
              key={procedure.id}
              procedure={procedure}
              onRemove={() => handleRemoveCode(procedure.id)}
              onUpdateDate={(date) => handleUpdateDate(procedure.id, date)}
              onMakePrincipal={() => handleMakePrincipal(procedure.id)}
            />
          ))}
        </div>
        <div className="mt-2">
          <CodeSearchInput
            codeType={searchCodeType}
            onSelect={(code) => handleAddCode(code, false)}
            placeholder={`Add secondary ${codeTypeLabel} procedure...`}
          />
        </div>
      </div>
    </div>
  )
}

interface ProcedureCodeCardProps {
  procedure: ProcedureCode
  onRemove: () => void
  onUpdateDate: (date: string) => void
  onMakePrincipal?: () => void
  isPrincipal?: boolean
}

function ProcedureCodeCard({
  procedure,
  onRemove,
  onUpdateDate,
  onMakePrincipal,
  isPrincipal,
}: ProcedureCodeCardProps) {
  return (
    <div
      className={`border rounded-md p-3 ${
        isPrincipal ? 'border-purple-300 bg-purple-50' : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-medium text-purple-600">{procedure.code}</span>
            <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
              {procedure.codeType}
            </span>
            {isPrincipal && (
              <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                Principal
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 mt-1 truncate">{procedure.description}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Date input */}
          <input
            type="date"
            value={procedure.procedureDate || ''}
            onChange={(e) => onUpdateDate(e.target.value)}
            className="text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-purple-500"
          />
          {/* Make Principal button */}
          {!isPrincipal && onMakePrincipal && (
            <button
              onClick={onMakePrincipal}
              className="text-xs text-purple-600 hover:text-purple-700"
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
