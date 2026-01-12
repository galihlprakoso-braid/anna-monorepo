from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload
from data.models.task import TaskModel
from api.core.exceptions import NotFoundError, ValidationError
from api.task.schemas import TaskCreate, TaskUpdate
from api.task.mapper import TaskMapper

class TaskService:
    """Business logic for task operations."""

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def create_task(self, schema: TaskCreate) -> TaskModel:
        """Create a new task."""
        # Validate parent exists
        if schema.parent_task_id:
            parent = self.db.get(TaskModel, schema.parent_task_id)
            if not parent:
                raise ValidationError(f"Parent task {schema.parent_task_id} not found")

        # Convert schema to model
        db_task = TaskMapper.from_create(schema, self.user_id)

        # Check for circular references
        if schema.parent_task_id:
            if self._would_create_cycle(schema.parent_task_id, db_task.id):
                raise ValidationError("Circular task reference detected")

        self.db.add(db_task)
        self.db.commit()

        # Re-fetch with subtasks loaded
        return self.get_task(db_task.id)

    def get_task(self, task_id: str) -> TaskModel:
        """Get task by ID."""
        # Eagerly load subtasks relationship
        stmt = select(TaskModel).where(TaskModel.id == task_id).options(selectinload(TaskModel.subtasks))
        task = self.db.execute(stmt).scalar_one_or_none()

        if not task or task.owner_user_id != self.user_id:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    def list_tasks(
        self,
        parent_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[TaskModel], int]:
        """List tasks with filtering and pagination."""
        query = select(TaskModel).where(TaskModel.owner_user_id == self.user_id)

        # Filter by parent
        if parent_id == "root":
            query = query.where(TaskModel.parent_task_id.is_(None))
        elif parent_id:
            query = query.where(TaskModel.parent_task_id == parent_id)

        # Filter by status
        if status:
            query = query.where(TaskModel.status == status)

        # Count total
        total = self.db.execute(select(func.count()).select_from(query.subquery())).scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        tasks = self.db.execute(query).scalars().all()
        return list(tasks), total

    def update_task(self, task_id: str, schema: TaskUpdate) -> TaskModel:
        """Update task."""
        task = self.get_task(task_id)

        # Validate parent change
        if schema.parent_task_id and schema.parent_task_id != task.parent_task_id:
            if self._would_create_cycle(schema.parent_task_id, task_id):
                raise ValidationError("Circular task reference detected")

        # Apply updates
        TaskMapper.apply_update(task, schema)

        self.db.commit()

        # Re-fetch with subtasks loaded
        return self.get_task(task_id)

    def delete_task(self, task_id: str, cascade: bool = False) -> bool:
        """Delete task."""
        task = self.get_task(task_id)

        if cascade:
            # Manually delete all subtasks recursively
            self._delete_subtasks_recursive(task)
        else:
            # Orphan subtasks (set parent_task_id to None)
            if task.subtasks:
                for subtask in task.subtasks:
                    subtask.parent_task_id = None
                    self.db.add(subtask)

        # Delete parent task
        self.db.delete(task)
        self.db.commit()
        return True

    def _would_create_cycle(self, parent_id: str, child_id: str) -> bool:
        """Check if setting parent_id would create a circular reference."""
        visited = set()
        current = parent_id

        while current:
            if current == child_id:
                return True
            if current in visited:
                break
            visited.add(current)

            parent_task = self.db.get(TaskModel, current)
            current = parent_task.parent_task_id if parent_task else None

        return False

    def _delete_subtasks_recursive(self, task: TaskModel):
        """Recursively delete all subtasks."""
        # Query for children directly (more reliable than relationship)
        children = self.db.execute(
            select(TaskModel).where(TaskModel.parent_task_id == task.id)
        ).scalars().all()

        for child in children:
            self._delete_subtasks_recursive(child)
            self.db.delete(child)
