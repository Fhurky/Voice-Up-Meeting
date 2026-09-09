# SQLAlchemy/Alembic profile

SQLAlchemy models under `app/backend/app/domain/models/` are the schema authority. Generate a
revision only after changing those models:

```sh
cd app/backend
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
alembic check
```

Read every generated revision before applying it. Alembic emits candidate migrations; data moves,
renames, and destructive changes still require explicit review. Never use `Base.metadata.create_all`
as a deployment mechanism.
