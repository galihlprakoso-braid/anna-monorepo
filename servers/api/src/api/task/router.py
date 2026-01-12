from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from data.core.database import get_db
from api.core.config import get_settings
from api.task.service import TaskService
from api.task.mapper import TaskMapper
from api.task.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from api.core.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse)
async def create_task(
    schema: TaskCreate,
    db: Session = Depends(get_db)
) -> TaskResponse:
    """Create a new task."""
    settings = get_settings()
    service = TaskService(db, settings.default_user_id)

    try:
        db_task = service.create_task(schema)
        return TaskMapper.to_response(db_task)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db)
) -> TaskResponse:
    """Get task by ID."""
    settings = get_settings()
    service = TaskService(db, settings.default_user_id)

    try:
        db_task = service.get_task(task_id)
        return TaskMapper.to_response(db_task)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    parent_id: str | None = Query(None, description="Parent task ID or 'root'"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> TaskListResponse:
    """List tasks with filtering and pagination."""
    settings = get_settings()
    service = TaskService(db, settings.default_user_id)

    tasks, total = service.list_tasks(
        parent_id=parent_id,
        status=status,
        page=page,
        page_size=page_size
    )

    return TaskListResponse(
        tasks=[TaskMapper.to_response(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size
    )

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    schema: TaskUpdate,
    db: Session = Depends(get_db)
) -> TaskResponse:
    """Update task."""
    settings = get_settings()
    service = TaskService(db, settings.default_user_id)

    try:
        db_task = service.update_task(task_id, schema)
        return TaskMapper.to_response(db_task)
    except (NotFoundError, ValidationError) as e:
        status_code = 404 if isinstance(e, NotFoundError) else 400
        raise HTTPException(status_code=status_code, detail=str(e))

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    cascade: bool = Query(False, description="Delete subtasks recursively"),
    db: Session = Depends(get_db)
) -> dict:
    """Delete task."""
    settings = get_settings()
    service = TaskService(db, settings.default_user_id)

    try:
        service.delete_task(task_id, cascade=cascade)
        return {"success": True}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
