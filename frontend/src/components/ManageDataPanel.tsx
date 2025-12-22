import { useState, useRef, useCallback } from 'react'
import { useUploadHL7 } from '../hooks/useUploadHL7'

interface ManageDataPanelProps {
  userRoles: string[]
}

export function ManageDataPanel({ userRoles }: ManageDataPanelProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    upload,
    isUploading,
    uploadResult,
    uploadError,
    uploadProgress,
    reset,
  } = useUploadHL7()

  // Check if user has coder or admin role
  const hasAccess = userRoles.some((role) =>
    ['coder', 'admin'].includes(role.toLowerCase())
  )

  // Don't render if user doesn't have access
  if (!hasAccess) {
    return null
  }

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return

    const newFiles = Array.from(files).filter((file) => {
      // Accept .hl7 files and text files
      const isValidType =
        file.name.toLowerCase().endsWith('.hl7') ||
        file.type === 'text/plain' ||
        file.type === ''
      return isValidType
    })

    setSelectedFiles((prev) => [...prev, ...newFiles])
    reset() // Clear previous results
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFileSelect(e.dataTransfer.files)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleUpload = () => {
    if (selectedFiles.length === 0) return
    upload(selectedFiles)
  }

  const handleClear = () => {
    setSelectedFiles([])
    reset()
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 mt-8">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Manage Data</h3>
      <p className="text-sm text-gray-600 mb-4">
        Upload HL7 message files to import patient encounters and clinical data.
      </p>

      {/* Drop Zone */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".hl7,text/plain"
          onChange={(e) => handleFileSelect(e.target.files)}
          className="hidden"
          id="hl7-file-input"
        />

        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>

        <p className="mt-2 text-sm text-gray-600">
          <label
            htmlFor="hl7-file-input"
            className="text-blue-600 hover:text-blue-500 cursor-pointer font-medium"
          >
            Click to upload
          </label>{' '}
          or drag and drop
        </p>
        <p className="mt-1 text-xs text-gray-500">HL7 files (.hl7 or .txt)</p>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="mt-4">
          <div className="flex justify-between items-center mb-2">
            <h4 className="text-sm font-medium text-gray-700">
              Selected Files ({selectedFiles.length})
            </h4>
            <button
              onClick={handleClear}
              className="text-xs text-gray-500 hover:text-gray-700"
              disabled={isUploading}
            >
              Clear all
            </button>
          </div>
          <ul className="space-y-2 max-h-40 overflow-y-auto">
            {selectedFiles.map((file, index) => (
              <li
                key={`${file.name}-${index}`}
                className="flex items-center justify-between bg-gray-50 rounded px-3 py-2 text-sm"
              >
                <div className="flex items-center gap-2 truncate">
                  <svg
                    className="h-4 w-4 text-gray-400 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <span className="truncate">{file.name}</span>
                  <span className="text-gray-400 flex-shrink-0">
                    ({formatFileSize(file.size)})
                  </span>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="text-gray-400 hover:text-red-500 ml-2"
                  disabled={isUploading}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Upload Button */}
      <div className="mt-4">
        <button
          onClick={handleUpload}
          disabled={selectedFiles.length === 0 || isUploading}
          className={`w-full py-2 px-4 rounded-md font-medium transition-colors ${
            selectedFiles.length === 0 || isUploading
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {isUploading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
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
              Uploading... {uploadProgress > 0 && `${uploadProgress}%`}
            </span>
          ) : (
            `Upload ${selectedFiles.length > 0 ? `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''}` : 'Files'}`
          )}
        </button>
      </div>

      {/* Upload Results */}
      {uploadResult && (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
          <h4 className="text-sm font-medium text-green-800 mb-2">Upload Complete</h4>
          <div className="text-sm text-green-700 space-y-1">
            <p>Files received: {uploadResult.files_received}</p>
            <p>Messages found: {uploadResult.messages_found}</p>
            <p>Messages processed: {uploadResult.messages_processed}</p>
            {uploadResult.encounters_created > 0 && (
              <p>Encounters created: {uploadResult.encounters_created}</p>
            )}
            {uploadResult.encounters_updated > 0 && (
              <p>Encounters updated: {uploadResult.encounters_updated}</p>
            )}
            {uploadResult.messages_failed > 0 && (
              <p className="text-yellow-700">
                Messages failed: {uploadResult.messages_failed}
              </p>
            )}
          </div>
          {uploadResult.errors.length > 0 && (
            <div className="mt-2">
              <p className="text-sm font-medium text-yellow-800">Warnings:</p>
              <ul className="text-xs text-yellow-700 list-disc list-inside">
                {uploadResult.errors.slice(0, 5).map((error, i) => (
                  <li key={i}>{error}</li>
                ))}
                {uploadResult.errors.length > 5 && (
                  <li>...and {uploadResult.errors.length - 5} more</li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Upload Error */}
      {uploadError && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <h4 className="text-sm font-medium text-red-800 mb-1">Upload Failed</h4>
          <p className="text-sm text-red-700">
            {uploadError instanceof Error
              ? uploadError.message
              : 'An error occurred while uploading files.'}
          </p>
        </div>
      )}
    </div>
  )
}
