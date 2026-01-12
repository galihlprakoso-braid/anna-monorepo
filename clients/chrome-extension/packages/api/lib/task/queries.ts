import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { Task, TaskListResponse } from './types';
import { apiClient } from '../client';

// Query keys
export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (filters?: { status?: string; parent_id?: string }) =>
    [...taskKeys.lists(), filters] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
};

// Fetch single task
export function useTask(taskId: string): UseQueryResult<Task, Error> {
  return useQuery({
    queryKey: taskKeys.detail(taskId),
    queryFn: async () => {
      return apiClient.get<Task>(`/tasks/${taskId}`);
    },
    enabled: !!taskId,
  });
}

// Fetch task list
interface UseTasksParams {
  parentId?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}

export function useTasks(params: UseTasksParams = {}): UseQueryResult<Task[], Error> {
  return useQuery({
    queryKey: taskKeys.list(params),
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params.parentId) searchParams.set('parent_id', params.parentId);
      if (params.status) searchParams.set('status', params.status);
      if (params.page) searchParams.set('page', params.page.toString());
      if (params.pageSize) searchParams.set('page_size', params.pageSize.toString());

      const query = searchParams.toString() ? `?${searchParams}` : '';
      const response = await apiClient.get<TaskListResponse>(`/tasks${query}`);
      return response.tasks;
    },
  });
}

// Fetch subtasks
export function useSubtasks(parentId: string): UseQueryResult<Task[], Error> {
  return useTasks({ parentId });
}

// Fetch root tasks (no parent)
export function useRootTasks(): UseQueryResult<Task[], Error> {
  return useTasks({ parentId: 'root' });
}
