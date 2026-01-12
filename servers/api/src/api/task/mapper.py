from datetime import datetime, UTC
from uuid import uuid4
from sqlalchemy.orm import object_session
from sqlalchemy import select
from data.models.task import TaskModel
from api.task.schemas import TaskCreate, TaskUpdate, TaskResponse

class TaskMapper:
    """Convert between SQLAlchemy TaskModel and Pydantic schemas."""

    @staticmethod
    def to_response(db_task: TaskModel) -> TaskResponse:
        """Convert SQLAlchemy model to Pydantic response schema."""
        # Get subtask IDs by querying (more reliable than relationship)
        session = object_session(db_task)
        subtask_ids = []
        if session:
            subtasks = session.execute(
                select(TaskModel.id).where(TaskModel.parent_task_id == db_task.id)
            ).scalars().all()
            subtask_ids = list(subtasks)

        return TaskResponse(
            id=db_task.id,
            title=db_task.title,
            description=db_task.description,
            status=db_task.status.value if hasattr(db_task.status, 'value') else db_task.status,
            priority=db_task.priority.value if hasattr(db_task.priority, 'value') else db_task.priority,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at,
            due_date=db_task.due_date,
            scheduled_date=db_task.scheduled_date,
            completed_at=db_task.completed_at,
            parent_task_id=db_task.parent_task_id,
            subtask_ids=subtask_ids,
            assignees=db_task.assignees,
            recurrence_config=db_task.recurrence_config,
            tags=db_task.tags,
            extra_data=db_task.extra_data,
            owner_user_id=db_task.owner_user_id,
        )

    @staticmethod
    def from_create(schema: TaskCreate, owner_user_id: str) -> TaskModel:
        """Convert Pydantic create schema to SQLAlchemy model."""
        now = datetime.now(UTC)
        return TaskModel(
            id=str(uuid4()),
            title=schema.title,
            description=schema.description,
            status=schema.status,
            priority=schema.priority,
            created_at=now,
            updated_at=now,
            due_date=schema.due_date,
            scheduled_date=schema.scheduled_date,
            parent_task_id=schema.parent_task_id,
            assignees=schema.assignees,
            recurrence_config=schema.recurrence_config,
            tags=schema.tags,
            extra_data=schema.extra_data,
            owner_user_id=owner_user_id,
        )

    @staticmethod
    def apply_update(db_task: TaskModel, schema: TaskUpdate) -> TaskModel:
        """Apply Pydantic update schema to SQLAlchemy model."""
        update_data = schema.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_task, field, value)

        db_task.updated_at = datetime.now(UTC)
        return db_task
