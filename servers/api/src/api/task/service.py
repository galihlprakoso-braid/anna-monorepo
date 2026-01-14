"""Service layer for Task business logic using MongoDB/Beanie."""

from datetime import datetime, UTC
from beanie import PydanticObjectId
from data.models.task import TaskDocument, TaskStatus
from api.core.exceptions import NotFoundError, ValidationError
from api.task.schemas import TaskCreate, TaskUpdate


class TaskService:
    """Business logic for task operations."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    async def create_task(self, schema: TaskCreate) -> TaskDocument:
        """Create a new task."""
        # Validate parent exists
        if schema.parent_task_id:
            parent = await TaskDocument.get(PydanticObjectId(schema.parent_task_id))
            if not parent or parent.owner_user_id != self.user_id:
                raise ValidationError(f"Parent task {schema.parent_task_id} not found")

        # Create document
        task = TaskDocument(
            title=schema.title,
            description=schema.description,
            status=schema.status,
            priority=schema.priority,
            due_date=schema.due_date,
            scheduled_date=schema.scheduled_date,
            parent_task_id=PydanticObjectId(schema.parent_task_id) if schema.parent_task_id else None,
            assignees=schema.assignees,
            recurrence_config=schema.recurrence_config,
            tags=schema.tags,
            extra_data=schema.extra_data,
            owner_user_id=self.user_id,
        )

        await task.insert()
        return task

    async def get_task(self, task_id: str) -> TaskDocument:
        """Get task by ID."""
        try:
            task = await TaskDocument.get(PydanticObjectId(task_id))
        except Exception:
            raise NotFoundError(f"Task {task_id} not found")

        if not task or task.owner_user_id != self.user_id:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def list_tasks(
        self,
        parent_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[TaskDocument], int]:
        """List tasks with filtering and pagination."""
        # Build query
        query = {"owner_user_id": self.user_id}

        # Filter by parent
        if parent_id == "root":
            query["parent_task_id"] = None
        elif parent_id:
            query["parent_task_id"] = PydanticObjectId(parent_id)

        # Filter by status
        if status:
            query["status"] = status

        # Count total
        total = await TaskDocument.find(query).count()

        # Paginate
        skip = (page - 1) * page_size
        tasks = await TaskDocument.find(query).skip(skip).limit(page_size).to_list()

        return tasks, total

    async def update_task(self, task_id: str, schema: TaskUpdate) -> TaskDocument:
        """Update task."""
        task = await self.get_task(task_id)

        # Get update data (excluding unset fields)
        update_data = schema.model_dump(exclude_unset=True)

        # Handle parent_task_id conversion
        if "parent_task_id" in update_data and update_data["parent_task_id"]:
            # Validate new parent exists
            new_parent_id = update_data["parent_task_id"]
            parent = await TaskDocument.get(PydanticObjectId(new_parent_id))
            if not parent or parent.owner_user_id != self.user_id:
                raise ValidationError(f"Parent task {new_parent_id} not found")

            # Check for circular reference
            if await self._would_create_cycle(new_parent_id, task_id):
                raise ValidationError("Circular task reference detected")

            update_data["parent_task_id"] = PydanticObjectId(new_parent_id)
        elif "parent_task_id" in update_data and update_data["parent_task_id"] is None:
            update_data["parent_task_id"] = None

        # Handle status change to completed
        if update_data.get("status") == TaskStatus.COMPLETED and task.status != TaskStatus.COMPLETED:
            update_data["completed_at"] = datetime.now(UTC)

        # Update timestamp
        update_data["updated_at"] = datetime.now(UTC)

        # Apply updates
        for field, value in update_data.items():
            setattr(task, field, value)

        await task.save()
        return task

    async def delete_task(self, task_id: str, cascade: bool = False) -> bool:
        """Delete task."""
        task = await self.get_task(task_id)

        if cascade:
            # Recursively delete all subtasks
            await self._delete_subtasks_recursive(str(task.id))

        else:
            # Orphan subtasks (set parent_task_id to None)
            subtasks = await TaskDocument.find(
                {"parent_task_id": task.id}
            ).to_list()
            for subtask in subtasks:
                subtask.parent_task_id = None
                await subtask.save()

        # Delete parent task
        await task.delete()
        return True

    async def _would_create_cycle(self, parent_id: str, child_id: str) -> bool:
        """Check if setting parent_id would create a circular reference."""
        visited = set()
        current = parent_id

        while current:
            if current == child_id:
                return True
            if current in visited:
                break
            visited.add(current)

            try:
                parent_task = await TaskDocument.get(PydanticObjectId(current))
                current = str(parent_task.parent_task_id) if parent_task and parent_task.parent_task_id else None
            except Exception:
                break

        return False

    async def _delete_subtasks_recursive(self, task_id: str):
        """Recursively delete all subtasks."""
        children = await TaskDocument.find(
            {"parent_task_id": PydanticObjectId(task_id)}
        ).to_list()

        for child in children:
            await self._delete_subtasks_recursive(str(child.id))
            await child.delete()
