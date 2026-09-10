"""Local administrator login configuration and real HTTP request-origin boundaries."""

from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.auth.endpoints import get_auth_service
from app.core.config import Settings, get_settings
from app.main import create_application

pytestmark = pytest.mark.unit


def settings(**values: object) -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret=get_settings().jwt_secret,
        **{"environment": "development", **values},
    )


def test_local_admin_is_disabled_by_default() -> None:
    configured = settings()
    assert configured.local_admin_login_enabled is False
    assert configured.local_admin_username == ""


@pytest.mark.parametrize("environment", ["test", "staging", "production"])
def test_local_admin_cannot_be_enabled_outside_development(environment: str) -> None:
    with pytest.raises(ValidationError, match="local_admin_login_enabled"):
        settings(environment=environment, local_admin_login_enabled=True)


def test_local_admin_username_is_normalized() -> None:
    assert (
        settings(local_admin_username="  Existing-Admin  ").local_admin_username == "existing-admin"
    )


def test_local_admin_openapi_declares_errors_without_accepting_credentials() -> None:
    contract = create_application().openapi()
    operation = contract["paths"]["/api/voiceup/v1/auth/local-admin"]["post"]
    assert "requestBody" not in operation
    assert not operation.get("security")
    for code in ("404", "503"):
        assert operation["responses"][code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/LocalAdminErrorResponse"
        }
    detail = contract["components"]["schemas"]["LocalAdminErrorDetail"]
    assert set(detail["required"]) == {"code", "message"}
    assert set(detail["properties"]["code"]["enum"]) == {"not_found", "local_admin_unavailable"}


@pytest.fixture
def application() -> Iterator:
    app = create_application()
    app.dependency_overrides[get_settings] = lambda: settings(local_admin_login_enabled=True)

    def unexpected_service():
        raise AssertionError("Rejected requests and options must not resolve an account")

    app.dependency_overrides[get_auth_service] = unexpected_service
    yield app
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("base_url", "headers"),
    [
        ("http://127.0.0.1:8081", {}),
        ("http://localhost:8081", {"Origin": "http://localhost:8081"}),
        ("http://[::1]:8081", {"Origin": "http://[::1]:8081"}),
        ("https://localhost", {"Origin": "https://localhost:443"}),
        (
            "http://127.0.0.1:8081",
            {"Origin": "http://127.0.0.1:8081", "Sec-Fetch-Site": "same-origin"},
        ),
    ],
)
async def test_options_permit_only_explicit_local_requests(application, base_url, headers) -> None:
    async with AsyncClient(transport=ASGITransport(app=application), base_url=base_url) as client:
        response = await client.get("/api/voiceup/v1/auth/options", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"local_admin_login_enabled": True}
    assert response.headers["cache-control"] == "no-store"


REJECTED_HEADERS = [
    {"Host": "example.test:8081"},
    {"Host": "127.0.0.1.example.test:8081"},
    {"Host": "localhost:0"},
    {"Host": "localhost:65536"},
    {"Host": "localhost:"},
    {"Host": "user@localhost:8081"},
    {"Host": "localhost:8081/path"},
    {"Origin": "null"},
    {"Origin": "http://example.test:8081"},
    {"Origin": "http://127.0.0.1:8082"},
    {"Origin": "https://127.0.0.1:8081"},
    {"Origin": "http://localhost:8081"},
    {"Origin": "http://127.0.0.1:8081/"},
    {"Origin": "http://user@127.0.0.1:8081"},
    {"Origin": "http://127.0.0.1:8081?value=1"},
    {"Sec-Fetch-Site": "cross-site"},
    {"Sec-Fetch-Site": "same-site"},
    {"Sec-Fetch-Site": "none"},
    {"Sec-Fetch-Site": ""},
    [("Host", "127.0.0.1:8081"), ("Host", "localhost:8081")],
    [("Origin", "http://127.0.0.1:8081"), ("Origin", "http://example.test")],
]


@pytest.mark.parametrize("headers", REJECTED_HEADERS)
async def test_nonlocal_requests_hide_options_and_cannot_login(application, headers) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://127.0.0.1:8081"
    ) as client:
        options = await client.get("/api/voiceup/v1/auth/options", headers=headers)
        login = await client.post("/api/voiceup/v1/auth/local-admin", headers=headers)
    assert options.status_code == 200
    assert options.json() == {"local_admin_login_enabled": False}
    assert options.headers["cache-control"] == "no-store"
    assert login.status_code == 404
    assert login.json()["detail"]["code"] == "not_found"
    assert login.headers["cache-control"] == "no-store"


async def test_disabled_mode_is_unavailable_without_database_access(application) -> None:
    application.dependency_overrides[get_settings] = lambda: settings()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://127.0.0.1:8081"
    ) as client:
        options = await client.get("/api/voiceup/v1/auth/options")
        login = await client.post("/api/voiceup/v1/auth/local-admin")
    assert options.json() == {"local_admin_login_enabled": False}
    assert login.status_code == 404
    assert login.headers["cache-control"] == "no-store"
