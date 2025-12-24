import { Link } from 'react-router-dom'
import { ReactNode } from 'react'

interface DashboardTileProps {
  title: string
  description: string
  to: string
  icon: ReactNode
  disabled?: boolean
}

export function DashboardTile({ title, description, to, icon, disabled }: DashboardTileProps) {
  if (disabled) {
    return (
      <div className="p-8 rounded-lg border border-gray-200 bg-gray-50 cursor-not-allowed opacity-60">
        <div className="flex flex-col items-center text-center">
          <div className="text-gray-400 mb-4">{icon}</div>
          <h3 className="text-xl font-semibold text-gray-600">{title}</h3>
          <p className="text-sm text-gray-400 mt-2">{description}</p>
        </div>
      </div>
    )
  }

  return (
    <Link
      to={to}
      className="p-8 rounded-lg border border-gray-200 bg-white hover:border-blue-400 hover:shadow-md transition-all"
    >
      <div className="flex flex-col items-center text-center">
        <div className="text-blue-600 mb-4">{icon}</div>
        <h3 className="text-xl font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-600 mt-2">{description}</p>
      </div>
    </Link>
  )
}
