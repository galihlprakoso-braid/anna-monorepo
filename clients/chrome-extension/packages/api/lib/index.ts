// Re-export client
export { apiClient, APIClient } from './client.js';
export { queryClient } from './query-client.js';

// Re-export types
export * from './task/types.js';
export * from './data-source/types.js';

// Re-export hooks
export {
  useTask,
  useTasks,
  useSubtasks,
  useRootTasks,
  taskKeys,
} from './task/queries.js';

export {
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
  useToggleTask,
} from './task/mutations.js';

export {
  useDataSource,
  useDataSources,
  useDataSourceTemplates,
  dataSourceKeys,
} from './data-source/queries.js';

export {
  useCreateDataSource,
  useCreateFromTemplate,
  useUpdateDataSource,
  useDeleteDataSource,
  useToggleDataSource,
} from './data-source/mutations.js';

export { triggerDataCollection } from './data-source/actions.js';
