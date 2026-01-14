"""FastAPI router for Task endpoints using MongoDB."""

from fastapi import APIRouter, HTTPException, Query
from api.core.config import get_settings
from api.task.service import TaskService
from api.task.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from api.core.exceptions import NotFoundError, ValidationError
from data.models.task import TaskDocument

router = APIRouter(prefix="/tasks", tags=["tasks"])


def task_to_response(task: TaskDocument) -> TaskResponse:
    """Convert TaskDocument to TaskResponse."""
    return TaskResponse(
        id=str(task.id),
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        scheduled_date=task.scheduled_date,
        parent_task_id=str(task.parent_task_id) if task.parent_task_id else None,
        assignees=task.assignees,
        recurrence_config=task.recurrence_config,
        tags=task.tags,
        extra_data=task.extra_data,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        owner_user_id=task.owner_user_id,
    )


@router.post("/", response_model=TaskResponse)
async def create_task(schema: TaskCreate) -> TaskResponse:
    """Create a new task."""
    settings = get_settings()
    service = TaskService(settings.default_user_id)

    try:
        task = await service.create_task(schema)
        return task_to_response(task)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """Get task by ID."""
    settings = get_settings()
    service = TaskService(settings.default_user_id)

    try:
        task = await service.get_task(task_id)
        return task_to_response(task)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    parent_id: str | None = Query(None, description="Parent task ID or 'root'"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> TaskListResponse:
    """List tasks with filtering and pagination."""
    settings = get_settings()
    service = TaskService(settings.default_user_id)

    tasks, total = await service.list_tasks(
        parent_id=parent_id,
        status=status,
        page=page,
        page_size=page_size
    )

    return TaskListResponse(
        tasks=[task_to_response(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size
    )


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, schema: TaskUpdate) -> TaskResponse:
    """Update task."""
    settings = get_settings()
    service = TaskService(settings.default_user_id)

    try:
        task = await service.update_task(task_id, schema)
        return task_to_response(task)
    except (NotFoundError, ValidationError) as e:
        status_code = 404 if isinstance(e, NotFoundError) else 400
        raise HTTPException(status_code=status_code, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    cascade: bool = Query(False, description="Delete subtasks recursively")
) -> dict:
    """Delete task."""
    settings = get_settings()
    service = TaskService(settings.default_user_id)

    try:
        await service.delete_task(task_id, cascade=cascade)
        return {"success": True}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
