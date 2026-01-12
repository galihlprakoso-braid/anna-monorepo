export enum TaskStatus {
  TODO = 'todo',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
}

export enum TaskPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent',
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  created_at: string; // ISO datetime
  updated_at: string;
  due_date?: string;
  scheduled_date?: string;
  completed_at?: string;
  parent_task_id?: string;
  subtask_ids: string[];
  assignees?: string[];
  recurrence_config?: Record<string, unknown>;
  tags?: string[];
  extra_data?: Record<string, unknown>;
  owner_user_id: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string;
  scheduled_date?: string;
  parent_task_id?: string;
  assignees?: string[];
  recurrence_config?: Record<string, unknown>;
  tags?: string[];
  extra_data?: Record<string, unknown>;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string;
  scheduled_date?: string;
  completed_at?: string;
  parent_task_id?: string;
  assignees?: string[];
  recurrence_config?: Record<string, unknown>;
  tags?: string[];
  extra_data?: Record<string, unknown>;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  page: number;
  page_size: number;
}
