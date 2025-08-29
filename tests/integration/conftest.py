"""Integration test configuration."""

import importlib.util
from collections.abc import Generator
from dataclasses import dataclass

import pytest
from testcontainers.postgres import PostgresContainer


@dataclass
class PostgresContainerInfo:
    """PostgreSQL container information."""

    url_sync: str
    url_async: str


@pytest.fixture(scope="session")
def pg_container() -> Generator[PostgresContainerInfo, None, None]:
    """Start PostgreSQL container for integration tests."""
    # Check if docker is available
    if importlib.util.find_spec("docker") is None:
        pytest.skip(
            "Docker not available. Install docker package to run integration tests.",
            allow_module_level=True,
        )

    # Start PostgreSQL 16 container
    postgres = PostgresContainer(
        image="postgres:16",
        username="protectogram_test",
        password="protectogram_test",
        dbname="protectogram_test",
    )

    with postgres as container:
        # Get mapped port
        mapped_port = container.get_exposed_port(5432)

        # Construct URLs
        url_sync = f"postgresql+psycopg://protectogram_test:protectogram_test@127.0.0.1:{mapped_port}/protectogram_test"
        url_async = f"postgresql+asyncpg://protectogram_test:protectogram_test@127.0.0.1:{mapped_port}/protectogram_test"

        yield PostgresContainerInfo(url_sync=url_sync, url_async=url_async)
