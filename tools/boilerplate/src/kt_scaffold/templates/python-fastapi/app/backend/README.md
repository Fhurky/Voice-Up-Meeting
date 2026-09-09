# @@PRODUCT_SLUG@@ Python backend

This profile is a neutral FastAPI platform baseline. It contains tenant context, JWT login,
`/auth/me`, RBAC guards, an application-level `super_admin`, PostgreSQL readiness, Alembic, and
OpenAPI export. It intentionally contains no business entity.

From the scaffold root:

```sh
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r app/backend/requirements.txt -r app/backend/requirements-dev.txt
cp app/backend/.env.example app/backend/.env
cd app/backend
alembic upgrade head
python -m app.scripts.create_super_admin
uvicorn app.main:app --reload
```

Login uses JSON `{ "username": "...", "password": "..." }` at
`@@API_PREFIX@@/auth/login`. Send the returned bearer token and the
`@@TENANT_HEADER@@` header to `@@API_PREFIX@@/auth/me`. The login response contains the home tenant's
public identifier.

Useful checks:

```sh
black --check app tests
isort --check-only app tests
mypy app
pytest
alembic check
python -m app.scripts.export_openapi
```

PostgreSQL integration tests run only when `RUN_POSTGRES_INTEGRATION=1`; point
`@@ENV_PREFIX@@DATABASE_URL` at a disposable database whose name ends in `_test`.

## Controlled container builds

`Dockerfile.dev` accepts `PYTHON_BASE_IMAGE`; bank pipelines must set it to the approved
internal-registry image including its immutable digest. Credentials and repository configuration
belong in a BuildKit `pip_conf` secret, never in a build argument or image layer. The default
`connected` dependency mode supports an approved connected artifact factory:

```sh
docker buildx build --load \
  --build-arg PYTHON_BASE_IMAGE='<internal-registry>/platform/python:3.13-alpine3.23@sha256:<digest>' \
  --secret id=pip_conf,src=/approved/build-secrets/pip.conf \
  -f app/backend/Dockerfile.dev .
```

For an air-gapped build, first verify the supplied bundle's `SHA256SUMS`, import/promote its base
images, and inject its profile wheelhouse as the named build context:

```sh
docker buildx build --load --network=none \
  --build-arg PYTHON_BASE_IMAGE='<internal-registry>/platform/python:3.13-alpine3.23@sha256:<digest>' \
  --build-arg DEPENDENCY_MODE=offline \
  --build-context python_wheelhouse=/approved/bundle/wheelhouse/python-fastapi \
  -f app/backend/Dockerfile.dev .
```

Offline mode forces `pip --no-index` and ignores every pip configuration file, so a missing wheel
fails the build instead of reaching another repository. The process runs as UID/GID `10001` by
default; controlled developer images may align bind-mount ownership with `APP_UID` and `APP_GID`.
