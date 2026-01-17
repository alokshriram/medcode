import { useState } from 'react'
import { SnapshotData } from '../../../api/codingQueue'
import { DocumentTree, DocumentCategory } from './DocumentTree'
import { DocumentContent } from './DocumentContent'

interface DocumentViewerProps {
  snapshot: SnapshotData
}

export function DocumentViewer({ snapshot }: DocumentViewerProps) {
  const [selectedCategory, setSelectedCategory] = useState<DocumentCategory>('encounter')
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <div className="flex h-full bg-gray-50">
      {/* Left sidebar - Document Tree */}
      <div className="w-56 border-r border-gray-200 bg-white overflow-y-auto flex-shrink-0">
        <DocumentTree
          snapshot={snapshot}
          selectedCategory={selectedCategory}
          selectedItemId={selectedItemId}
          onSelectCategory={setSelectedCategory}
          onSelectItem={setSelectedItemId}
        />
      </div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Search bar */}
        <div className="border-b border-gray-200 bg-white px-4 py-2">
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search in documents..."
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <XIcon className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          <DocumentContent
            snapshot={snapshot}
            category={selectedCategory}
            selectedItemId={selectedItemId}
            searchQuery={searchQuery}
          />
        </div>
      </div>
    </div>
  )
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  )
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}
