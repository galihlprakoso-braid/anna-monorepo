// Re-export client
export { apiClient, APIClient } from './client';
export { queryClient } from './query-client';

// Re-export types
export * from './task/types';

// Re-export hooks
export {
  useTask,
  useTasks,
  useSubtasks,
  useRootTasks,
  taskKeys,
} from './task/queries';

export {
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
  useToggleTask,
} from './task/mutations';
