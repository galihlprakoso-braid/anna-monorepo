/**
 * React Query mutations for Data Source operations
 */

import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import { apiClient } from '../client.js';
import type { DataSource, DataSourceCreate, DataSourceUpdate } from './types.js';
import { dataSourceKeys } from './queries.js';

/**
 * Create a new data source
 */
export function useCreateDataSource(): UseMutationResult<
  DataSource,
  Error,
  DataSourceCreate,
  unknown
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DataSourceCreate) =>
      apiClient.request<DataSource>('/data-sources', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dataSourceKeys.lists() });
    },
  });
}

/**
 * Create a data source from a template
 */
export function useCreateFromTemplate(): UseMutationResult<DataSource, Error, string, unknown> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (templateId: string) =>
      apiClient.request<DataSource>(`/data-sources/templates/${templateId}/create`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dataSourceKeys.lists() });
    },
  });
}

/**
 * Update an existing data source
 */
export function useUpdateDataSource(): UseMutationResult<
  DataSource,
  Error,
  { id: string; data: DataSourceUpdate },
  unknown
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) =>
      apiClient.request<DataSource>(`/data-sources/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: dataSourceKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: dataSourceKeys.lists() });
    },
  });
}

/**
 * Delete a data source
 */
export function useDeleteDataSource(): UseMutationResult<void, Error, string, unknown> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      apiClient.request<void>(`/data-sources/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dataSourceKeys.all });
    },
  });
}

/**
 * Toggle data source status (active <-> paused)
 */
export function useToggleDataSource(): UseMutationResult<DataSource, Error, string, unknown> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      // Fetch current status
      const current = await apiClient.request<DataSource>(`/data-sources/${id}`);
      const newStatus = current.status === 'active' ? 'paused' : 'active';

      // Toggle status
      return apiClient.request<DataSource>(`/data-sources/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
    },
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: dataSourceKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: dataSourceKeys.lists() });
    },
  });
}
