"""Safe test defaults loaded before application modules."""

import os

import pytest
from sqlalchemy.engine import make_url

os.environ.setdefault("VOICEUP_ENVIRONMENT", "test")
# Local Compose deliberately enables this convenience; tests opt in per application fixture.
os.environ["VOICEUP_LOCAL_ADMIN_LOGIN_ENABLED"] = "false"
os.environ["VOICEUP_LOCAL_ADMIN_USERNAME"] = ""
os.environ.setdefault(
    "VOICEUP_JWT_SECRET",
    "unit-test-secret-do-not-deploy-at-least-32-bytes",
)
os.environ.setdefault(
    "VOICEUP_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/voiceup_test",
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
    url = os.environ["VOICEUP_DATABASE_URL"]
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        pytest.fail("integration tests require a disposable database ending in '_test'")
    return url
