import { createStorage, StorageEnum } from '../base/index.js';

/**
 * Minimal DataSource interface for storage
 * Full definition is in @extension/api
 */
export interface DataSource {
  id: string;
  name: string;
  description?: string;
  source_type: string;
  status: string;
  target_url?: string;
  instruction?: string;
  schedule_interval_minutes: number;
  [key: string]: unknown; // Allow additional properties
}

export interface DataSourceCache {
  dataSources: DataSource[];
  lastSyncAt: number;
}

export const dataSourceStorage = createStorage<DataSourceCache>(
  'data-sources-cache',
  {
    dataSources: [],
    lastSyncAt: 0,
  },
  {
    storageEnum: StorageEnum.Local,
    liveUpdate: true,
  },
);
