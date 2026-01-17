import { useState, useRef, useCallback, useEffect } from 'react'

interface SplitPaneProps {
  left: React.ReactNode
  right: React.ReactNode
  defaultLeftWidth?: number // percentage, default 50
  minLeftWidth?: number // percentage, default 30
  maxLeftWidth?: number // percentage, default 70
}

export function SplitPane({
  left,
  right,
  defaultLeftWidth = 50,
  minLeftWidth = 30,
  maxLeftWidth = 70,
}: SplitPaneProps) {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return

      const containerRect = containerRef.current.getBoundingClientRect()
      const containerWidth = containerRect.width
      const mouseX = e.clientX - containerRect.left

      let newLeftWidth = (mouseX / containerWidth) * 100

      // Clamp to min/max
      newLeftWidth = Math.max(minLeftWidth, Math.min(maxLeftWidth, newLeftWidth))

      setLeftWidth(newLeftWidth)
    },
    [isDragging, minLeftWidth, maxLeftWidth]
  )

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isDragging, handleMouseMove, handleMouseUp])

  return (
    <div ref={containerRef} className="flex h-full w-full overflow-hidden">
      {/* Left Panel */}
      <div
        className="h-full overflow-auto"
        style={{ width: `${leftWidth}%`, flexShrink: 0 }}
      >
        {left}
      </div>

      {/* Drag Handle */}
      <div
        className={`w-1 h-full cursor-col-resize flex-shrink-0 transition-colors ${
          isDragging ? 'bg-blue-500' : 'bg-gray-200 hover:bg-gray-300'
        }`}
        onMouseDown={handleMouseDown}
      />

      {/* Right Panel */}
      <div className="flex-1 h-full overflow-auto">{right}</div>
    </div>
  )
}
