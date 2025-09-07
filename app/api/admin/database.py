"""Admin database management endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import BaseAppSettings
from app.dependencies import get_settings
from app.database import AsyncSessionLocal
from .models import DatabaseResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/database", tags=["admin-database"])


def verify_admin_key(
    x_admin_key: Annotated[str, Header(alias="X-Admin-Key")] = None,
    settings: BaseAppSettings = Depends(get_settings),
) -> bool:
    """
    Verify admin API key for protected database endpoints.

    Args:
        x_admin_key: Admin key from X-Admin-Key header
        settings: Application settings

    Returns:
        True if authentication successful

    Raises:
        HTTPException: If authentication fails
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin key required. Provide X-Admin-Key header.",
        )

    # Get admin key from environment, fallback to secret_key for dev/staging
    import os

    admin_key = os.getenv("DATABASE_ADMIN_KEY")
    if not admin_key:
        if settings.environment in ["development", "staging"]:
            admin_key = settings.secret_key
            logger.warning(
                f"Using SECRET_KEY for database admin auth in {settings.environment}. Set DATABASE_ADMIN_KEY for production."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database admin key not configured",
            )

    if x_admin_key != admin_key:
        logger.warning(f"Invalid database admin key attempt from {x_admin_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key"
        )

    return True


@router.delete("/clear-test-data", response_model=DatabaseResponse)
async def clear_test_data(
    _: bool = Depends(verify_admin_key),
    settings: BaseAppSettings = Depends(get_settings),
):
    """
    Clear all test data from the database (staging/development only).

    This endpoint safely truncates all user data tables while preserving
    the database schema. Strictly forbidden in production for safety.

    Returns:
        DatabaseResponse: Confirmation of data clearing
    """
    # Safety check: Never allow in production
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Database clearing is strictly forbidden in production for safety",
        )

    # Additional safety check for staging/development
    if settings.environment not in ["staging", "development"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Database clearing only available in staging/development, current: {settings.environment}",
        )

    logger.info(f"Database clear requested in {settings.environment} environment")

    try:
        async with AsyncSessionLocal() as session:
            # Clear tables in dependency order to avoid foreign key constraints
            tables_to_clear = [
                "user_guardians",
                "guardians",
                "users",
                "panic_notification_attempts",
                "panic_alerts",
                "trips",  # Add if trips table exists
            ]

            cleared_tables = []

            for table in tables_to_clear:
                try:
                    # Check if table exists first
                    result = await session.execute(
                        text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_schema = 'public'
                            AND table_name = :table_name
                        )
                        """),
                        {"table_name": table},
                    )

                    table_exists = result.scalar()

                    if table_exists:
                        # Get count before clearing
                        count_result = await session.execute(
                            text(f"SELECT COUNT(*) FROM {table}")
                        )
                        row_count = count_result.scalar()

                        # Clear the table
                        await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                        cleared_tables.append(f"{table} ({row_count} rows)")
                        logger.info(f"Cleared table {table}: {row_count} rows")
                    else:
                        logger.info(f"Table {table} does not exist, skipping")

                except SQLAlchemyError as e:
                    logger.warning(f"Could not clear table {table}: {e}")
                    continue

            # Commit the transaction
            await session.commit()

            message = f"Successfully cleared {len(cleared_tables)} tables in {settings.environment}"
            logger.info(message)

            return DatabaseResponse(
                status="success",
                message=message,
                environment=settings.environment,
                cleared_tables=cleared_tables,
                details=f"Cleared tables: {', '.join([t.split(' ')[0] for t in cleared_tables])}",
            )

    except SQLAlchemyError as e:
        error_msg = f"Database error while clearing data: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )
    except Exception as e:
        error_msg = f"Unexpected error while clearing database: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )


@router.get("/status", response_model=DatabaseResponse)
async def get_database_status(
    _: bool = Depends(verify_admin_key),
    settings: BaseAppSettings = Depends(get_settings),
):
    """
    Get database status and table row counts.

    Returns:
        DatabaseResponse: Current database status
    """
    try:
        async with AsyncSessionLocal() as session:
            tables_info = []

            # Get table row counts
            tables_to_check = [
                "users",
                "guardians",
                "user_guardians",
                "panic_alerts",
                "panic_notification_attempts",
            ]

            for table in tables_to_check:
                try:
                    # Check if table exists
                    result = await session.execute(
                        text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_schema = 'public'
                            AND table_name = :table_name
                        )
                        """),
                        {"table_name": table},
                    )

                    if result.scalar():
                        count_result = await session.execute(
                            text(f"SELECT COUNT(*) FROM {table}")
                        )
                        row_count = count_result.scalar()
                        tables_info.append(f"{table}: {row_count} rows")
                    else:
                        tables_info.append(f"{table}: table not found")

                except SQLAlchemyError as e:
                    tables_info.append(f"{table}: error - {str(e)}")

            return DatabaseResponse(
                status="success",
                message=f"Database status for {settings.environment}",
                environment=settings.environment,
                details="; ".join(tables_info),
            )

    except Exception as e:
        error_msg = f"Error getting database status: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )
