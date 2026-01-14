/**
 * TypeScript types for Data Source API
 */

export enum DataSourceType {
  OAUTH = 'oauth',
  BROWSER_AGENT = 'browser_agent',
}

export enum DataSourceStatus {
  ACTIVE = 'active',
  PAUSED = 'paused',
  ERROR = 'error',
  PENDING = 'pending',
}

export enum OAuthProvider {
  GMAIL = 'gmail',
  GOOGLE_CALENDAR = 'google_calendar',
}

export interface DataSource {
  id: string;
  name: string;
  description?: string;
  source_type: DataSourceType;
  status: DataSourceStatus;

  // OAuth fields
  oauth_provider?: OAuthProvider;

  // Browser Agent fields
  target_url?: string;
  instruction?: string;

  // Scheduling
  schedule_interval_minutes: number;

  // Tracking
  last_run_at?: string;
  next_run_at?: string;
  run_count: number;
  success_count: number;
  error_count: number;
  last_error?: string;

  // Config
  config?: Record<string, unknown>;

  // Ownership
  owner_user_id: string;
  created_at: string;
  updated_at: string;

  // Template flag
  is_template: boolean;
}

export interface DataSourceCreate {
  name: string;
  description?: string;
  source_type: DataSourceType;
  status?: DataSourceStatus;
  oauth_provider?: OAuthProvider;
  target_url?: string;
  instruction?: string;
  schedule_interval_minutes?: number;
  config?: Record<string, unknown>;
}

export interface DataSourceUpdate {
  name?: string;
  description?: string;
  status?: DataSourceStatus;
  target_url?: string;
  instruction?: string;
  schedule_interval_minutes?: number;
  config?: Record<string, unknown>;
}

export interface DataSourceListResponse {
  items: DataSource[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TemplateListResponse {
  templates: DataSource[];
}

export interface DataSourceListParams {
  source_type?: DataSourceType;
  status?: DataSourceStatus;
  page?: number;
  page_size?: number;
}
