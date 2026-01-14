"""Pydantic schemas for DataSource API."""

from pydantic import BaseModel, Field
from datetime import datetime
from data.models.datasource import DataSourceType, DataSourceStatus, OAuthProvider


class DataSourceBase(BaseModel):
    """Base schema for data source."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    source_type: DataSourceType
    status: DataSourceStatus = DataSourceStatus.PENDING

    # OAuth fields
    oauth_provider: OAuthProvider | None = None

    # Browser Agent fields
    target_url: str | None = None
    instruction: str | None = None

    # Scheduling
    schedule_interval_minutes: int = Field(default=60, ge=1)

    # Config
    config: dict | None = None


class DataSourceCreate(DataSourceBase):
    """Schema for creating a data source."""

    pass


class DataSourceUpdate(BaseModel):
    """Schema for updating a data source."""

    name: str | None = None
    description: str | None = None
    status: DataSourceStatus | None = None
    target_url: str | None = None
    instruction: str | None = None
    schedule_interval_minutes: int | None = Field(default=None, ge=1)
    config: dict | None = None


class DataSourceResponse(DataSourceBase):
    """Schema for data source response."""

    model_config = {"from_attributes": True}

    id: str

    # Tracking (read-only)
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    run_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_error: str | None = None

    # Ownership
    owner_user_id: str
    created_at: datetime
    updated_at: datetime

    # Template flag
    is_template: bool = False


class DataSourceListResponse(BaseModel):
    """Schema for paginated list of data sources."""

    items: list[DataSourceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TemplateListResponse(BaseModel):
    """Schema for list of templates."""

    templates: list[DataSourceResponse]
