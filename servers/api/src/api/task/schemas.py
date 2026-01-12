from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskBase(BaseModel):
    """Base task schema."""
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    scheduled_date: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    assignees: Optional[list[str]] = None
    recurrence_config: Optional[dict] = None
    tags: Optional[list[str]] = None
    extra_data: Optional[dict] = None

class TaskCreate(TaskBase):
    """Schema for creating a task."""
    pass

class TaskUpdate(BaseModel):
    """Schema for updating a task (all fields optional)."""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    scheduled_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    assignees: Optional[list[str]] = None
    recurrence_config: Optional[dict] = None
    tags: Optional[list[str]] = None
    extra_data: Optional[dict] = None

class TaskResponse(TaskBase):
    """Schema for task response."""
    model_config = {"from_attributes": True}  # Enable ORM mode

    id: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    owner_user_id: str
    subtask_ids: list[str] = []

class TaskListResponse(BaseModel):
    """Schema for list of tasks."""
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int
