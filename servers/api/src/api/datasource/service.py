"""Service layer for DataSource business logic using MongoDB/Beanie."""

from datetime import datetime, UTC
from beanie import PydanticObjectId
from data.models.datasource import (
    DataSourceDocument,
    DataSourceType,
    DataSourceStatus,
)
from api.datasource.schemas import DataSourceCreate, DataSourceUpdate
from api.core.exceptions import NotFoundError, ValidationError


class DataSourceService:
    """Service for DataSource business logic."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    async def create_datasource(self, schema: DataSourceCreate) -> DataSourceDocument:
        """Create a new data source."""
        # Validation
        self._validate_datasource_fields(schema)

        # Create document
        datasource = DataSourceDocument(
            name=schema.name,
            description=schema.description,
            source_type=schema.source_type,
            status=schema.status,
            oauth_provider=schema.oauth_provider,
            target_url=schema.target_url,
            instruction=schema.instruction,
            schedule_interval_minutes=schema.schedule_interval_minutes,
            config=schema.config,
            owner_user_id=self.user_id,
        )

        await datasource.insert()
        return datasource

    async def get_datasource(self, datasource_id: str) -> DataSourceDocument:
        """Get a data source by ID."""
        try:
            datasource = await DataSourceDocument.get(PydanticObjectId(datasource_id))
        except Exception:
            raise NotFoundError(f"DataSource {datasource_id} not found")

        if not datasource or datasource.owner_user_id != self.user_id:
            raise NotFoundError(f"DataSource {datasource_id} not found")

        return datasource

    async def list_datasources(
        self,
        source_type: DataSourceType | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[DataSourceDocument], int]:
        """List all data sources with filtering and pagination."""
        # Build query
        query = {
            "owner_user_id": self.user_id,
            "is_template": False,  # Exclude templates from user list
        }

        if source_type:
            query["source_type"] = source_type
        if status:
            query["status"] = status

        # Count total
        total = await DataSourceDocument.find(query).count()

        # Paginate and sort
        skip = (page - 1) * page_size
        datasources = await (
            DataSourceDocument.find(query)
            .sort(-DataSourceDocument.created_at)
            .skip(skip)
            .limit(page_size)
            .to_list()
        )

        return datasources, total

    async def list_templates(self) -> list[DataSourceDocument]:
        """Get all template data sources (system-owned)."""
        templates = await (
            DataSourceDocument.find({"is_template": True})
            .sort(DataSourceDocument.name)
            .to_list()
        )
        return templates

    async def create_from_template(self, template_id: str) -> DataSourceDocument:
        """Clone a template into user's data sources."""
        # Get template
        try:
            template = await DataSourceDocument.get(PydanticObjectId(template_id))
        except Exception:
            raise NotFoundError(f"Template {template_id} not found")

        if not template or not template.is_template:
            raise NotFoundError(f"Template {template_id} not found")

        # Clone to user's datasources
        schema = DataSourceCreate(
            name=template.name,
            description=template.description,
            source_type=template.source_type,
            status=DataSourceStatus.ACTIVE,
            oauth_provider=template.oauth_provider,
            target_url=template.target_url,
            instruction=template.instruction,
            schedule_interval_minutes=template.schedule_interval_minutes,
            config=template.config,
        )

        return await self.create_datasource(schema)

    async def update_datasource(
        self, datasource_id: str, schema: DataSourceUpdate
    ) -> DataSourceDocument:
        """Update a data source."""
        datasource = await self.get_datasource(datasource_id)

        # Get update data (excluding unset fields)
        update_data = schema.model_dump(exclude_unset=True)

        # Validate updates
        if update_data:
            self._validate_datasource_fields(schema, is_update=True)

        # Update timestamp
        update_data["updated_at"] = datetime.now(UTC)

        # Apply updates
        for field, value in update_data.items():
            setattr(datasource, field, value)

        await datasource.save()
        return datasource

    async def delete_datasource(self, datasource_id: str) -> None:
        """Delete a data source."""
        datasource = await self.get_datasource(datasource_id)
        await datasource.delete()

    def _validate_datasource_fields(self, schema, is_update=False):
        """Validate data source fields based on type."""
        # Get fields
        if is_update:
            data = schema.model_dump(exclude_unset=True)
            source_type = data.get("source_type")
        else:
            data = schema.model_dump()
            source_type = schema.source_type

        if source_type == DataSourceType.OAUTH:
            if not is_update and not data.get("oauth_provider"):
                raise ValidationError(
                    "oauth_provider required for OAuth data sources"
                )
            if data.get("target_url") or data.get("instruction"):
                raise ValidationError(
                    "target_url and instruction not allowed for OAuth data sources"
                )

        elif source_type == DataSourceType.BROWSER_AGENT:
            if not is_update:
                if not data.get("target_url"):
                    raise ValidationError(
                        "target_url required for Browser Agent data sources"
                    )
                if not data.get("instruction"):
                    raise ValidationError(
                        "instruction required for Browser Agent data sources"
                    )
            if data.get("oauth_provider"):
                raise ValidationError(
                    "oauth_provider not allowed for Browser Agent data sources"
                )
