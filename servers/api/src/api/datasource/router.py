"""FastAPI router for DataSource endpoints using MongoDB."""

import math
from fastapi import APIRouter, HTTPException, Query
from api.core.config import get_settings
from api.core.exceptions import NotFoundError, ValidationError
from api.datasource.schemas import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    DataSourceListResponse,
    TemplateListResponse,
)
from api.datasource.service import DataSourceService
from data.models.datasource import DataSourceDocument


router = APIRouter(prefix="/data-sources", tags=["data-sources"])


def datasource_to_response(ds: DataSourceDocument) -> DataSourceResponse:
    """Convert DataSourceDocument to DataSourceResponse."""
    return DataSourceResponse(
        id=str(ds.id),
        name=ds.name,
        description=ds.description,
        source_type=ds.source_type,
        status=ds.status,
        oauth_provider=ds.oauth_provider,
        target_url=ds.target_url,
        instruction=ds.instruction,
        schedule_interval_minutes=ds.schedule_interval_minutes,
        config=ds.config,
        last_run_at=ds.last_run_at,
        next_run_at=ds.next_run_at,
        run_count=ds.run_count,
        success_count=ds.success_count,
        error_count=ds.error_count,
        last_error=ds.last_error,
        owner_user_id=ds.owner_user_id,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
        is_template=ds.is_template,
    )


@router.post("/", response_model=DataSourceResponse, status_code=201)
async def create_datasource(schema: DataSourceCreate) -> DataSourceResponse:
    """Create a new data source."""
    settings = get_settings()
    service = DataSourceService(settings.default_user_id)

    try:
        datasource = await service.create_datasource(schema)
        return datasource_to_response(datasource)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates() -> TemplateListResponse:
    """Get all available data source templates."""
    settings = get_settings()
    service = DataSourceService(settings.default_user_id)

    templates = await service.list_templates()

    return TemplateListResponse(
        templates=[datasource_to_response(t) for t in templates]
    )


@router.post(
    "/templates/{template_id}/create", response_model=DataSourceResponse, status_code=201
)
async def create_from_template(template_id: str) -> DataSourceResponse:
    """Create a new data source from a template."""
    settings = get_settings()
    service = DataSourceService(settings.default_user_id)

    try:
        datasource = await service.create_from_template(template_id)
        return datasource_to_response(datasource)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{datasource_id}", response_model=DataSourceResponse)
async def get_datasource(datasource_id: str) -> DataSourceResponse:
    """Get a data source by ID."""
    settings = get_settings()
    service = DataSourceService(settings.default_user_id)

    try:
        datasource = await service.get_datasource(datasource_id)
        return datasource_to_response(datasource)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/", response_model=DataSourceListResponse)
async def list_datasources(
    source_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> DataSourceListResponse:
    """List all data sources with filtering and pagination."""
    settings = get_settings()
    service = DataSourceService(settings.default_user_id)

    datasources, total = await service.list_datasources(
        source_type=source_type, status=status, page=page, page_size=page_size
    )

    return DataSourceListResponse(
        items=[datasource_to_response(ds) for ds in datasources],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.patch("/{datasource_id}", response_model=DataSourceResponse)
async def update_datasource(
    datasource_id: str, schema: DataSourceUpdate
) -> DataSourceResponse:
    """Update a data source."""
    settings = get_settings()
    service = DataSourceService(settings.default_user_id)

    try:
        datasource = await service.update_datasource(datasource_id, schema)
        return datasource_to_response(datasource)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{datasource_id}", status_code=204)
async def delete_datasource(datasource_id: str) -> None:
    """Delete a data source."""
    settings = get_settings()
    service = DataSourceService(settings.default_user_id)

    try:
        await service.delete_datasource(datasource_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
