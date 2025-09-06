"""Pydantic models for admin migration endpoints."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MigrationResponse(BaseModel):
    """Response model for migration operations."""

    status: str = Field(..., description="Operation status: success, error, or started")
    message: str = Field(..., description="Human-readable message about the operation")
    current_revision: Optional[str] = Field(
        None, description="Current database revision"
    )
    pending_migrations: Optional[List[str]] = Field(
        None, description="List of pending migration revisions"
    )
    applied_migrations: Optional[List[str]] = Field(
        None, description="List of recently applied migrations"
    )
    output: Optional[str] = Field(None, description="Raw command output for debugging")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class MigrationRequest(BaseModel):
    """Request model for migration operations."""

    revision: str = Field(default="head", description="Target revision (default: head)")
    message: Optional[str] = Field(
        None, description="Migration message (for generation)"
    )
    autogenerate: bool = Field(
        default=False, description="Auto-generate migration from model changes"
    )


class MigrationStatusResponse(BaseModel):
    """Detailed response for migration status endpoint."""

    status: str
    message: str
    current_revision: Optional[str] = None
    database_exists: bool
    alembic_table_exists: bool
    pending_count: int = 0
    pending_migrations: List[str] = []
    migration_history: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DatabaseResponse(BaseModel):
    """Response model for database operations."""

    status: str = Field(..., description="Operation status: success or error")
    message: str = Field(..., description="Human-readable message about the operation")
    environment: Optional[str] = Field(None, description="Current environment")
    cleared_tables: Optional[List[str]] = Field(
        None, description="List of cleared tables with row counts"
    )
    details: Optional[str] = Field(None, description="Additional operation details")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
