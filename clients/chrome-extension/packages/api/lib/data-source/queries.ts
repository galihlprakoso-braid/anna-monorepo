/**
 * React Query hooks for Data Source queries
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { apiClient } from '../client.js';
import type {
  DataSource,
  DataSourceListResponse,
  DataSourceListParams,
  TemplateListResponse,
} from './types.js';

export const dataSourceKeys = {
  all: ['data-sources'] as const,
  lists: () => [...dataSourceKeys.all, 'list'] as const,
  list: (params: DataSourceListParams) => [...dataSourceKeys.lists(), params] as const,
  details: () => [...dataSourceKeys.all, 'detail'] as const,
  detail: (id: string) => [...dataSourceKeys.details(), id] as const,
  templates: () => [...dataSourceKeys.all, 'templates'] as const,
};

/**
 * Fetch a single data source by ID
 */
export function useDataSource(id: string): UseQueryResult<DataSource, Error> {
  return useQuery({
    queryKey: dataSourceKeys.detail(id),
    queryFn: () => apiClient.request<DataSource>(`/data-sources/${id}`),
  });
}

/**
 * Fetch list of data sources with filtering and pagination
 */
export function useDataSources(
  params: DataSourceListParams = {},
): UseQueryResult<DataSourceListResponse, Error> {
  return useQuery({
    queryKey: dataSourceKeys.list(params),
    queryFn: () => {
      const searchParams = new URLSearchParams();
      if (params.source_type) searchParams.set('source_type', params.source_type);
      if (params.status) searchParams.set('status', params.status);
      if (params.page) searchParams.set('page', params.page.toString());
      if (params.page_size) searchParams.set('page_size', params.page_size.toString());

      const query = searchParams.toString() ? `?${searchParams}` : '';
      return apiClient.request<DataSourceListResponse>(`/data-sources${query}`);
    },
  });
}

/**
 * Fetch all available data source templates
 */
export function useDataSourceTemplates(): UseQueryResult<TemplateListResponse, Error> {
  return useQuery({
    queryKey: dataSourceKeys.templates(),
    queryFn: () => apiClient.request<TemplateListResponse>('/data-sources/templates'),
  });
}
