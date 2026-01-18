import { useMemo } from 'react'
import { SnapshotData } from '../../../api/codingQueue'

export type DocumentCategory =
  | 'documents'
  | 'diagnoses'
  | 'procedures'
  | 'observations'
  | 'orders'
  | 'encounter'

export interface TreeItem {
  id: string
  label: string
  category: DocumentCategory
  count?: number
}

interface DocumentTreeProps {
  snapshot: SnapshotData
  selectedCategory: DocumentCategory
  selectedItemId: string | null
  onSelectCategory: (category: DocumentCategory) => void
  onSelectItem: (itemId: string | null) => void
}

export function DocumentTree({
  snapshot,
  selectedCategory,
  selectedItemId,
  onSelectCategory,
  onSelectItem,
}: DocumentTreeProps) {
  const categories = useMemo(() => {
    return [
      {
        id: 'encounter',
        label: 'Encounter Info',
        category: 'encounter' as DocumentCategory,
        icon: ClipboardIcon,
      },
      {
        id: 'documents',
        label: 'Documents',
        category: 'documents' as DocumentCategory,
        count: snapshot.documents.length,
        icon: DocumentIcon,
      },
      {
        id: 'diagnoses',
        label: 'Diagnoses',
        category: 'diagnoses' as DocumentCategory,
        count: snapshot.diagnoses.length,
        icon: HeartIcon,
      },
      {
        id: 'procedures',
        label: 'Procedures',
        category: 'procedures' as DocumentCategory,
        count: snapshot.procedures.length,
        icon: ScissorsIcon,
      },
      {
        id: 'observations',
        label: 'Observations',
        category: 'observations' as DocumentCategory,
        count: snapshot.observations.length,
        icon: ChartIcon,
      },
      {
        id: 'orders',
        label: 'Orders',
        category: 'orders' as DocumentCategory,
        count: snapshot.orders.length,
        icon: ListIcon,
      },
    ]
  }, [snapshot])

  const getItemsForCategory = (category: DocumentCategory) => {
    switch (category) {
      case 'documents':
        return snapshot.documents.map((d) => ({
          id: d.id,
          label: d.document_type || 'Unknown Document',
          sublabel: d.author,
        }))
      case 'diagnoses':
        return snapshot.diagnoses.map((d) => ({
          id: d.id,
          label: d.diagnosis_code || 'Unknown',
          sublabel: d.diagnosis_description,
        }))
      case 'procedures':
        return snapshot.procedures.map((p) => ({
          id: p.id,
          label: p.procedure_code || 'Unknown',
          sublabel: p.procedure_description,
        }))
      case 'observations':
        return snapshot.observations.map((o) => ({
          id: o.id,
          label: o.observation_identifier || 'Unknown',
          sublabel: o.observation_value,
        }))
      case 'orders':
        return snapshot.orders.map((o) => ({
          id: o.id,
          label: o.order_type || 'Unknown',
          sublabel: o.ordering_provider,
        }))
      default:
        return []
    }
  }

  const currentItems = getItemsForCategory(selectedCategory)

  return (
    <div className="h-full flex flex-col">
      {/* Category list */}
      <div className="border-b border-gray-200">
        <div className="p-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
          Categories
        </div>
        <nav className="space-y-1 pb-2">
          {categories.map((cat) => {
            const Icon = cat.icon
            const isSelected = selectedCategory === cat.category
            return (
              <button
                key={cat.id}
                onClick={() => {
                  onSelectCategory(cat.category)
                  onSelectItem(null)
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors ${
                  isSelected
                    ? 'bg-blue-50 text-blue-700 border-l-2 border-blue-600'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="flex-1 truncate">{cat.label}</span>
                {cat.count !== undefined && (
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded-full ${
                      isSelected ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {cat.count}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Items in selected category */}
      {selectedCategory !== 'encounter' && currentItems.length > 0 && (
        <div className="flex-1 overflow-y-auto">
          <div className="p-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
            {selectedCategory}
          </div>
          <nav className="space-y-1 pb-2">
            {currentItems.map((item) => (
              <button
                key={item.id}
                onClick={() => onSelectItem(item.id)}
                className={`w-full px-3 py-2 text-left transition-colors ${
                  selectedItemId === item.id
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <div className="text-sm font-medium truncate">{item.label}</div>
                {item.sublabel && (
                  <div className="text-xs text-gray-500 truncate">{item.sublabel}</div>
                )}
              </button>
            ))}
          </nav>
        </div>
      )}
    </div>
  )
}

// Simple inline icons
function ClipboardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
    </svg>
  )
}

function DocumentIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}

function HeartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
    </svg>
  )
}

function ScissorsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z" />
    </svg>
  )
}

function ChartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  )
}

function ListIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
    </svg>
  )
}
