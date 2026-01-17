import { useState, useRef, useEffect } from 'react'
import { useCatalogSearch } from '../../../hooks/useCatalogSearch'

export type CodeType = 'ICD-10-CM' | 'ICD-10-PCS' | 'CPT'

interface CodeResult {
  code: string
  description: string
}

interface CodeSearchInputProps {
  codeType: CodeType
  onSelect: (code: CodeResult) => void
  placeholder?: string
}

export function CodeSearchInput({ codeType, onSelect, placeholder }: CodeSearchInputProps) {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { data: searchResults, isLoading } = useCatalogSearch(query, query.length >= 2)

  // Filter results based on code type
  const filteredResults: CodeResult[] = (() => {
    if (!searchResults) return []

    if (codeType === 'CPT') {
      return searchResults.cpt_codes.map((c) => ({
        code: c.code,
        description: c.description,
      }))
    }
    // Both ICD-10-CM and ICD-10-PCS use icd10_codes
    // Note: In a real implementation, you'd want to filter by code pattern
    // ICD-10-CM: typically alpha + 2-7 chars (e.g., A00.0)
    // ICD-10-PCS: 7 alphanumeric chars (e.g., 0016070)
    return searchResults.icd10_codes.map((c) => ({
      code: c.code,
      description: c.description,
    }))
  })()

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (result: CodeResult) => {
    onSelect(result)
    setQuery('')
    setIsOpen(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false)
    }
  }

  return (
    <div className="relative">
      <div className="relative">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setIsOpen(true)
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || `Search ${codeType} codes...`}
          className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {isLoading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <LoadingSpinner />
          </div>
        )}
      </div>

      {/* Dropdown */}
      {isOpen && query.length >= 2 && (
        <div
          ref={dropdownRef}
          className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto"
        >
          {filteredResults.length === 0 && !isLoading && (
            <div className="px-4 py-3 text-sm text-gray-500">No codes found</div>
          )}
          {filteredResults.map((result, index) => (
            <button
              key={`${result.code}-${index}`}
              onClick={() => handleSelect(result)}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 focus:bg-gray-50 focus:outline-none"
            >
              <span className="font-mono text-sm text-blue-600">{result.code}</span>
              <p className="text-sm text-gray-600 truncate">{result.description}</p>
            </button>
          ))}
        </div>
      )}
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

function LoadingSpinner() {
  return (
    <svg className="animate-spin h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}
