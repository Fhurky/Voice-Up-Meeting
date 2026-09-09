"""Safe test defaults loaded before application modules."""

import os

import pytest
from sqlalchemy.engine import make_url

os.environ.setdefault("@@ENV_PREFIX@@ENVIRONMENT", "test")
os.environ.setdefault(
    "@@ENV_PREFIX@@JWT_SECRET",
    "unit-test-secret-do-not-deploy-at-least-32-bytes",
)
os.environ.setdefault(
    "@@ENV_PREFIX@@DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/@@PRODUCT_SLUG@@_test",
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("RUN_POSTGRES_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="set RUN_POSTGRES_INTEGRATION=1 for PostgreSQL tests")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def postgres_database_url() -> str:
    url = os.environ["@@ENV_PREFIX@@DATABASE_URL"]
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        pytest.fail("integration tests require a disposable database ending in '_test'")
    return url
