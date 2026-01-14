import { useMutation, useQueryClient, UseMutationResult } from '@tanstack/react-query';
import { Task, TaskCreate, TaskUpdate, TaskStatus, TaskPriority } from './types.js';
import { apiClient } from '../client.js';
import { taskKeys } from './queries.js';

// Create task
interface CreateTaskParams {
  title: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  parentTaskId?: string;
  dueDate?: Date;
  scheduledDate?: Date;
}

export function useCreateTask(): UseMutationResult<Task, Error, CreateTaskParams> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: CreateTaskParams) => {
      const payload: TaskCreate = {
        title: params.title,
        description: params.description,
        status: params.status || TaskStatus.TODO,
        priority: params.priority || TaskPriority.MEDIUM,
        due_date: params.dueDate?.toISOString(),
        scheduled_date: params.scheduledDate?.toISOString(),
        parent_task_id: params.parentTaskId,
      };

      return apiClient.post<Task>('/tasks', payload);
    },
    onSuccess: (newTask) => {
      // Invalidate task lists
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });

      // If it has a parent, invalidate parent's detail
      if (newTask.parent_task_id) {
        queryClient.invalidateQueries({ queryKey: taskKeys.detail(newTask.parent_task_id) });
      }
    },
  });
}

// Update task
interface UpdateTaskParams {
  id: string;
  updates: TaskUpdate;
}

export function useUpdateTask(): UseMutationResult<Task, Error, UpdateTaskParams> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: UpdateTaskParams) => {
      return apiClient.patch<Task>(`/tasks/${params.id}`, params.updates);
    },
    onSuccess: (updatedTask) => {
      // Update task in cache
      queryClient.setQueryData(taskKeys.detail(updatedTask.id), updatedTask);

      // Invalidate task lists
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}

// Delete task
interface DeleteTaskParams {
  id: string;
  cascade?: boolean;
}

export function useDeleteTask(): UseMutationResult<boolean, Error, DeleteTaskParams> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: DeleteTaskParams) => {
      const query = params.cascade ? '?cascade=true' : '';
      await apiClient.delete(`/tasks/${params.id}${query}`);
      return true;
    },
    onSuccess: (_, variables) => {
      // Remove task from cache
      queryClient.removeQueries({ queryKey: taskKeys.detail(variables.id) });

      // Invalidate task lists
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}

// Toggle task completion
export function useToggleTask(): UseMutationResult<Task, Error, string> {
  const updateTask = useUpdateTask();

  return useMutation({
    mutationFn: async (taskId: string) => {
      const task = await apiClient.get<Task>(`/tasks/${taskId}`);

      const newStatus =
        task.status === TaskStatus.COMPLETED
          ? TaskStatus.TODO
          : TaskStatus.COMPLETED;

      const updates: TaskUpdate = {
        status: newStatus,
        completed_at: newStatus === TaskStatus.COMPLETED ? new Date().toISOString() : undefined,
      };

      return updateTask.mutateAsync({ id: taskId, updates });
    },
  });
}
