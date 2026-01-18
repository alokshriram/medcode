import { useMemo } from 'react'
import { SnapshotData } from '../../../api/codingQueue'
import { DocumentCategory } from './DocumentTree'

interface DocumentContentProps {
  snapshot: SnapshotData
  category: DocumentCategory
  selectedItemId: string | null
  searchQuery: string
}

export function DocumentContent({
  snapshot,
  category,
  selectedItemId,
  searchQuery,
}: DocumentContentProps) {
  const content = useMemo(() => {
    switch (category) {
      case 'encounter':
        return <EncounterInfo snapshot={snapshot} />
      case 'documents':
        return (
          <DocumentsList
            documents={snapshot.documents}
            selectedId={selectedItemId}
            searchQuery={searchQuery}
          />
        )
      case 'diagnoses':
        return (
          <DiagnosesList
            diagnoses={snapshot.diagnoses}
            selectedId={selectedItemId}
            searchQuery={searchQuery}
          />
        )
      case 'procedures':
        return (
          <ProceduresList
            procedures={snapshot.procedures}
            selectedId={selectedItemId}
            searchQuery={searchQuery}
          />
        )
      case 'observations':
        return (
          <ObservationsList
            observations={snapshot.observations}
            selectedId={selectedItemId}
            searchQuery={searchQuery}
          />
        )
      case 'orders':
        return (
          <OrdersList
            orders={snapshot.orders}
            selectedId={selectedItemId}
            searchQuery={searchQuery}
          />
        )
      default:
        return null
    }
  }, [snapshot, category, selectedItemId, searchQuery])

  return <div className="h-full overflow-y-auto p-4">{content}</div>
}

function EncounterInfo({ snapshot }: { snapshot: SnapshotData }) {
  const { patient, encounter } = snapshot

  return (
    <div className="space-y-6">
      {/* Patient Info */}
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Patient Information</h3>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">Name</dt>
              <dd className="text-sm text-gray-900">
                {patient.name_family}, {patient.name_given}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">MRN</dt>
              <dd className="text-sm text-gray-900">{patient.mrn || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Date of Birth</dt>
              <dd className="text-sm text-gray-900">
                {patient.date_of_birth ? formatDate(patient.date_of_birth) : '-'}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Gender</dt>
              <dd className="text-sm text-gray-900">{patient.gender || '-'}</dd>
            </div>
          </dl>
        </div>
      </section>

      {/* Encounter Info */}
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Encounter Details</h3>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">Visit Number</dt>
              <dd className="text-sm text-gray-900">{encounter.visit_number || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Encounter Type</dt>
              <dd className="text-sm text-gray-900">{encounter.encounter_type || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Service Line</dt>
              <dd className="text-sm text-gray-900">{encounter.service_line || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Status</dt>
              <dd className="text-sm text-gray-900">{encounter.status || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Admit Date</dt>
              <dd className="text-sm text-gray-900">
                {encounter.admit_datetime ? formatDateTime(encounter.admit_datetime) : '-'}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Discharge Date</dt>
              <dd className="text-sm text-gray-900">
                {encounter.discharge_datetime ? formatDateTime(encounter.discharge_datetime) : '-'}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-sm font-medium text-gray-500">Admitting Diagnosis</dt>
              <dd className="text-sm text-gray-900">{encounter.admitting_diagnosis || '-'}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-sm font-medium text-gray-500">Discharge Disposition</dt>
              <dd className="text-sm text-gray-900">{encounter.discharge_disposition || '-'}</dd>
            </div>
          </dl>
        </div>
      </section>
    </div>
  )
}

function DocumentsList({
  documents,
  selectedId,
  searchQuery,
}: {
  documents: SnapshotData['documents']
  selectedId: string | null
  searchQuery: string
}) {
  const filteredDocs = useMemo(() => {
    if (!searchQuery) return documents
    const query = searchQuery.toLowerCase()
    return documents.filter(
      (d) =>
        d.content?.toLowerCase().includes(query) ||
        d.document_type?.toLowerCase().includes(query) ||
        d.author?.toLowerCase().includes(query)
    )
  }, [documents, searchQuery])

  if (filteredDocs.length === 0) {
    return <EmptyState message="No documents found" />
  }

  // If an item is selected, show only that document
  if (selectedId) {
    const doc = documents.find((d) => d.id === selectedId)
    if (doc) {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">{doc.document_type || 'Document'}</h3>
            <span className="text-sm text-gray-500">
              {doc.origination_datetime ? formatDateTime(doc.origination_datetime) : ''}
            </span>
          </div>
          {doc.author && <p className="text-sm text-gray-500">Author: {doc.author}</p>}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
              {highlightText(doc.content || 'No content available', searchQuery)}
            </pre>
          </div>
        </div>
      )
    }
  }

  // Show all documents
  return (
    <div className="space-y-4">
      {filteredDocs.map((doc) => (
        <div key={doc.id} className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-medium text-gray-900">{doc.document_type || 'Document'}</h4>
            <span className="text-xs text-gray-500">
              {doc.origination_datetime ? formatDateTime(doc.origination_datetime) : ''}
            </span>
          </div>
          {doc.author && <p className="text-xs text-gray-500 mb-2">Author: {doc.author}</p>}
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono line-clamp-6">
            {highlightText(doc.content || 'No content', searchQuery)}
          </pre>
        </div>
      ))}
    </div>
  )
}

function DiagnosesList({
  diagnoses,
  selectedId,
  searchQuery,
}: {
  diagnoses: SnapshotData['diagnoses']
  selectedId: string | null
  searchQuery: string
}) {
  const filteredDiagnoses = useMemo(() => {
    if (!searchQuery) return diagnoses
    const query = searchQuery.toLowerCase()
    return diagnoses.filter(
      (d) =>
        d.diagnosis_code?.toLowerCase().includes(query) ||
        d.diagnosis_description?.toLowerCase().includes(query)
    )
  }, [diagnoses, searchQuery])

  if (filteredDiagnoses.length === 0) {
    return <EmptyState message="No diagnoses found" />
  }

  const displayDiagnoses = selectedId
    ? diagnoses.filter((d) => d.id === selectedId)
    : filteredDiagnoses

  return (
    <div className="space-y-2">
      <h3 className="text-lg font-semibold text-gray-900 mb-3">Diagnoses from Source</h3>
      {displayDiagnoses.map((d) => (
        <div key={d.id} className="bg-white rounded-lg border border-gray-200 p-3">
          <div className="flex items-start gap-3">
            <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
              {highlightText(d.diagnosis_code || 'N/A', searchQuery)}
            </span>
            <div className="flex-1">
              <p className="text-sm text-gray-900">
                {highlightText(d.diagnosis_description || 'No description', searchQuery)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Type: {d.diagnosis_type || 'Unknown'} | Method: {d.coding_method || 'Unknown'}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function ProceduresList({
  procedures,
  selectedId,
  searchQuery,
}: {
  procedures: SnapshotData['procedures']
  selectedId: string | null
  searchQuery: string
}) {
  const filteredProcedures = useMemo(() => {
    if (!searchQuery) return procedures
    const query = searchQuery.toLowerCase()
    return procedures.filter(
      (p) =>
        p.procedure_code?.toLowerCase().includes(query) ||
        p.procedure_description?.toLowerCase().includes(query) ||
        p.performing_physician?.toLowerCase().includes(query)
    )
  }, [procedures, searchQuery])

  if (filteredProcedures.length === 0) {
    return <EmptyState message="No procedures found" />
  }

  const displayProcedures = selectedId
    ? procedures.filter((p) => p.id === selectedId)
    : filteredProcedures

  return (
    <div className="space-y-2">
      <h3 className="text-lg font-semibold text-gray-900 mb-3">Procedures from Source</h3>
      {displayProcedures.map((p) => (
        <div key={p.id} className="bg-white rounded-lg border border-gray-200 p-3">
          <div className="flex items-start gap-3">
            <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
              {highlightText(p.procedure_code || 'N/A', searchQuery)}
            </span>
            <div className="flex-1">
              <p className="text-sm text-gray-900">
                {highlightText(p.procedure_description || 'No description', searchQuery)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {p.procedure_datetime ? formatDateTime(p.procedure_datetime) : 'No date'}
                {p.performing_physician && ` | Surgeon: ${p.performing_physician}`}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function ObservationsList({
  observations,
  selectedId,
  searchQuery,
}: {
  observations: SnapshotData['observations']
  selectedId: string | null
  searchQuery: string
}) {
  const filteredObs = useMemo(() => {
    if (!searchQuery) return observations
    const query = searchQuery.toLowerCase()
    return observations.filter(
      (o) =>
        o.observation_identifier?.toLowerCase().includes(query) ||
        o.observation_value?.toLowerCase().includes(query)
    )
  }, [observations, searchQuery])

  if (filteredObs.length === 0) {
    return <EmptyState message="No observations found" />
  }

  const displayObs = selectedId ? observations.filter((o) => o.id === selectedId) : filteredObs

  return (
    <div className="space-y-2">
      <h3 className="text-lg font-semibold text-gray-900 mb-3">Observations / Lab Results</h3>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Test
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Value
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Reference
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Flag
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {displayObs.map((o) => (
              <tr key={o.id}>
                <td className="px-3 py-2 text-sm text-gray-900">
                  {highlightText(o.observation_identifier || '-', searchQuery)}
                </td>
                <td className="px-3 py-2 text-sm text-gray-900">
                  {highlightText(o.observation_value || '-', searchQuery)}
                  {o.units && <span className="text-gray-500 ml-1">{o.units}</span>}
                </td>
                <td className="px-3 py-2 text-sm text-gray-500">{o.reference_range || '-'}</td>
                <td className="px-3 py-2 text-sm">
                  {o.abnormal_flags && (
                    <span className="text-red-600 font-medium">{o.abnormal_flags}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function OrdersList({
  orders,
  selectedId,
  searchQuery,
}: {
  orders: SnapshotData['orders']
  selectedId: string | null
  searchQuery: string
}) {
  const filteredOrders = useMemo(() => {
    if (!searchQuery) return orders
    const query = searchQuery.toLowerCase()
    return orders.filter(
      (o) =>
        o.order_type?.toLowerCase().includes(query) ||
        o.ordering_provider?.toLowerCase().includes(query)
    )
  }, [orders, searchQuery])

  if (filteredOrders.length === 0) {
    return <EmptyState message="No orders found" />
  }

  const displayOrders = selectedId ? orders.filter((o) => o.id === selectedId) : filteredOrders

  return (
    <div className="space-y-2">
      <h3 className="text-lg font-semibold text-gray-900 mb-3">Orders</h3>
      {displayOrders.map((o) => (
        <div key={o.id} className="bg-white rounded-lg border border-gray-200 p-3">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">
                {highlightText(o.order_type || 'Unknown Order', searchQuery)}
              </p>
              <p className="text-xs text-gray-500">
                Provider: {highlightText(o.ordering_provider || 'Unknown', searchQuery)}
              </p>
            </div>
            <div className="text-right">
              <span
                className={`text-xs px-2 py-1 rounded ${
                  o.order_status === 'completed'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-yellow-100 text-yellow-700'
                }`}
              >
                {o.order_status || 'Unknown'}
              </span>
              <p className="text-xs text-gray-500 mt-1">
                {o.order_datetime ? formatDateTime(o.order_datetime) : ''}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-32 text-gray-500 text-sm">{message}</div>
  )
}

// Utility functions
function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString()
  } catch {
    return dateStr
  }
}

function formatDateTime(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString()
  } catch {
    return dateStr
  }
}

function highlightText(text: string, query: string): React.ReactNode {
  if (!query || !text) return text

  const parts = text.split(new RegExp(`(${escapeRegExp(query)})`, 'gi'))
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={i} className="bg-yellow-200">
        {part}
      </mark>
    ) : (
      part
    )
  )
}

function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
