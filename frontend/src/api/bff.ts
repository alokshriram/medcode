import { apiClient } from './client'

interface DashboardData {
  pending_tasks: number
  in_progress_tasks: number
  completed_tasks_today: number
  total_records: number
}

export const bffApi = {
  getDashboard: async (): Promise<DashboardData> => {
    const response = await apiClient.get<DashboardData>('/bff/dashboard')
    return response.data
  },

  getCodingWorkspace: async (taskId: string) => {
    const response = await apiClient.get(`/bff/coding-workspace/${taskId}`)
    return response.data
  },
}
