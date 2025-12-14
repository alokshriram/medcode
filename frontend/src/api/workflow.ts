import { apiClient } from './client'

interface CodingTask {
  id: string
  title: string
  description: string | null
  status: string
  priority: number
  assigned_to: string | null
  created_by: string
  due_date: string | null
  created_at: string
  updated_at: string
}

interface CreateTaskInput {
  title: string
  description?: string
  priority?: number
  assigned_to?: string
  due_date?: string
}

interface UpdateTaskInput {
  title?: string
  description?: string
  status?: string
  priority?: number
  assigned_to?: string
  due_date?: string
}

export const workflowApi = {
  getTasks: async (skip = 0, limit = 100): Promise<CodingTask[]> => {
    const response = await apiClient.get<CodingTask[]>('/workflow/tasks', {
      params: { skip, limit },
    })
    return response.data
  },

  getTask: async (taskId: string): Promise<CodingTask> => {
    const response = await apiClient.get<CodingTask>(`/workflow/tasks/${taskId}`)
    return response.data
  },

  createTask: async (task: CreateTaskInput): Promise<CodingTask> => {
    const response = await apiClient.post<CodingTask>('/workflow/tasks', task)
    return response.data
  },

  updateTask: async (taskId: string, task: UpdateTaskInput): Promise<CodingTask> => {
    const response = await apiClient.patch<CodingTask>(`/workflow/tasks/${taskId}`, task)
    return response.data
  },

  deleteTask: async (taskId: string): Promise<void> => {
    await apiClient.delete(`/workflow/tasks/${taskId}`)
  },
}
