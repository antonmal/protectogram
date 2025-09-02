"""Admin migration endpoints for database schema management."""

import os
import subprocess
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import BaseAppSettings
from app.dependencies import get_settings
from app.database import sync_engine
from .models import MigrationResponse, MigrationRequest, MigrationStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/migrations", tags=["admin-migrations"])


def verify_admin_key(
    x_admin_key: Annotated[str, Header(alias="X-Admin-Key")] = None,
    settings: BaseAppSettings = Depends(get_settings),
) -> bool:
    """
    Verify admin API key for protected migration endpoints.

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

    # Get admin key from environment, fallback to secret_key for dev
    admin_key = os.getenv("MIGRATION_ADMIN_KEY")
    if not admin_key:
        if settings.environment == "development":
            admin_key = settings.secret_key
            logger.warning(
                "Using SECRET_KEY for migration auth in development. Set MIGRATION_ADMIN_KEY for production."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Migration admin key not configured",
            )

    if x_admin_key != admin_key:
        logger.warning(f"Invalid migration admin key attempt from {x_admin_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key"
        )

    return True


@router.get("/status", response_model=MigrationStatusResponse)
async def get_migration_status(
    _: bool = Depends(verify_admin_key),
    settings: BaseAppSettings = Depends(get_settings),
):
    """
    Get detailed migration status including current revision and pending migrations.

    Returns comprehensive information about the database migration state.
    """
    try:
        database_exists = True
        alembic_table_exists = False
        current_revision = None
        migration_history = []

        # Check if we can connect to database and if alembic_version table exists
        try:
            with sync_engine.connect() as conn:
                # Check if alembic_version table exists
                result = conn.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'alembic_version'
                    );
                """
                    )
                )
                alembic_table_exists = result.scalar()

                if alembic_table_exists:
                    # Get current revision
                    result = conn.execute(
                        text("SELECT version_num FROM alembic_version LIMIT 1")
                    )
                    current_revision = result.scalar()

        except SQLAlchemyError as e:
            database_exists = False
            logger.error(f"Database connection failed: {e}")

        # Get migration history using alembic
        pending_migrations = []
        try:
            # Get history of migrations
            result = subprocess.run(
                ["alembic", "history", "--verbose"],
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URL": settings.database_url},
                timeout=30,
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if " -> " in line and "(head)" not in line:
                        # Extract revision ID
                        if "<base>" not in line:
                            revision = line.strip().split(" ")[0]
                            migration_history.append(revision)

                            # If this revision is not current, it's pending
                            if current_revision != revision:
                                pending_migrations.append(revision)

        except subprocess.TimeoutExpired:
            logger.warning("Alembic history command timed out")
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")

        return MigrationStatusResponse(
            status="success",
            message=f"Migration status for {settings.environment} environment",
            current_revision=current_revision,
            database_exists=database_exists,
            alembic_table_exists=alembic_table_exists,
            pending_count=len(pending_migrations),
            pending_migrations=pending_migrations[:5],  # Show latest 5
            migration_history=migration_history[:10],  # Show latest 10
        )

    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        return MigrationStatusResponse(
            status="error",
            message=f"Failed to retrieve migration status: {str(e)}",
            database_exists=False,
            alembic_table_exists=False,
            pending_count=0,
        )


@router.post("/upgrade", response_model=MigrationResponse)
async def run_migration_upgrade(
    request: MigrationRequest = MigrationRequest(),
    _: bool = Depends(verify_admin_key),
    settings: BaseAppSettings = Depends(get_settings),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Run database migrations (upgrade to specified revision).

    Upgrades the database schema to the target revision (default: head).
    In production, runs as background task to prevent timeouts.
    """
    logger.info(
        f"Migration upgrade requested: {request.revision} in {settings.environment}"
    )

    # For production, run in background to prevent timeout
    if settings.environment == "production":
        background_tasks.add_task(
            _run_migration_upgrade_task,
            settings.database_url,
            request.revision,
            settings.environment,
        )
        return MigrationResponse(
            status="started",
            message=f"Migration upgrade to '{request.revision}' started in background for production",
            applied_migrations=[request.revision],
        )

    # For dev/staging, run synchronously for immediate feedback
    try:
        result = subprocess.run(
            ["alembic", "upgrade", request.revision],
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": settings.database_url},
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"Migration failed: {result.stderr}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration failed: {result.stderr.strip()}",
            )

        # Get new current revision
        current_revision = None
        try:
            with sync_engine.connect() as conn:
                result_query = conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                current_revision = result_query.scalar()
        except Exception as e:
            logger.warning(f"Could not fetch current revision after upgrade: {e}")

        logger.info(f"Migration upgrade completed successfully to {current_revision}")
        return MigrationResponse(
            status="success",
            message=f"Successfully upgraded database to revision '{request.revision}'",
            current_revision=current_revision,
            applied_migrations=[request.revision],
            output=result.stdout.strip(),
        )

    except subprocess.TimeoutExpired:
        logger.error("Migration upgrade timed out")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Migration upgrade timed out after 5 minutes",
        )
    except Exception as e:
        logger.error(f"Migration upgrade failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration upgrade failed: {str(e)}",
        )


@router.post("/downgrade", response_model=MigrationResponse)
async def run_migration_downgrade(
    request: MigrationRequest,
    _: bool = Depends(verify_admin_key),
    settings: BaseAppSettings = Depends(get_settings),
):
    """
    Downgrade database migration (DANGER: use with extreme caution!).

    Rolls back database schema to the specified revision.
    Disabled in production for safety.
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Migration downgrade is disabled in production for safety",
        )

    if not request.revision or request.revision == "head":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specific revision required for downgrade (cannot use 'head')",
        )

    logger.warning(
        f"Migration downgrade requested: {request.revision} in {settings.environment}"
    )

    try:
        result = subprocess.run(
            ["alembic", "downgrade", request.revision],
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": settings.database_url},
            timeout=300,
        )

        if result.returncode != 0:
            logger.error(f"Migration downgrade failed: {result.stderr}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration downgrade failed: {result.stderr.strip()}",
            )

        logger.info(f"Migration downgrade completed to {request.revision}")
        return MigrationResponse(
            status="success",
            message=f"Successfully downgraded database to revision '{request.revision}'",
            current_revision=request.revision,
            output=result.stdout.strip(),
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Migration downgrade timed out after 5 minutes",
        )
    except Exception as e:
        logger.error(f"Migration downgrade failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration downgrade failed: {str(e)}",
        )


@router.post("/generate", response_model=MigrationResponse)
async def generate_migration(
    request: MigrationRequest,
    _: bool = Depends(verify_admin_key),
    settings: BaseAppSettings = Depends(get_settings),
):
    """
    Generate a new migration file based on model changes.

    Creates a new Alembic migration file with optional auto-generation
    from SQLAlchemy model changes.
    """
    if not request.message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Migration message is required for generation",
        )

    logger.info(
        f"Migration generation requested: '{request.message}' (autogenerate: {request.autogenerate})"
    )

    try:
        cmd = ["alembic", "revision"]

        if request.autogenerate:
            cmd.append("--autogenerate")

        cmd.extend(["-m", request.message])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": settings.database_url},
            timeout=60,
        )

        if result.returncode != 0:
            logger.error(f"Migration generation failed: {result.stderr}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration generation failed: {result.stderr.strip()}",
            )

        # Extract generated file name from output
        generated_file = None
        for line in result.stdout.split("\n"):
            if "Generating" in line and ".py" in line:
                generated_file = line.split("/")[-1].strip()
                break

        logger.info(f"Migration file generated: {generated_file}")
        return MigrationResponse(
            status="success",
            message=f"Migration generated: {generated_file or request.message}",
            output=result.stdout.strip(),
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Migration generation timed out after 1 minute",
        )
    except Exception as e:
        logger.error(f"Migration generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration generation failed: {str(e)}",
        )


async def _run_migration_upgrade_task(
    database_url: str, revision: str, environment: str
):
    """
    Background task for running migrations in production.

    Args:
        database_url: Database connection URL
        revision: Target revision to upgrade to
        environment: Current environment (for logging)
    """
    try:
        logger.info(
            f"Starting background migration upgrade to {revision} in {environment}"
        )

        result = subprocess.run(
            ["alembic", "upgrade", revision],
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": database_url},
            timeout=600,  # 10 minute timeout for production
            check=True,
        )

        logger.info(
            f"Background migration upgrade to {revision} completed successfully"
        )
        logger.debug(f"Migration output: {result.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Background migration upgrade failed: {e.stderr}")
        # In production, you might want to send this to Sentry or other error tracking

    except subprocess.TimeoutExpired:
        logger.error("Background migration upgrade timed out after 10 minutes")

    except Exception as e:
        logger.error(f"Background migration upgrade encountered unexpected error: {e}")
