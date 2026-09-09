"""Provision a DML-only role in VoiceUp's isolated local PostgreSQL container."""

from __future__ import annotations

import re
import secrets
import subprocess
from pathlib import Path

from local_runtime_config import dotenv_values


def provision_runtime(root: Path) -> None:
    env_path = root / "app/infra/.env"
    source = env_path.read_text(encoding="utf-8-sig") if env_path.exists() else ""
    configured = dotenv_values(source)
    password = configured.get("RUNTIME_DATABASE_PASSWORD", secrets.token_urlsafe(32))
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", password):
        raise SystemExit("RUNTIME_DATABASE_PASSWORD must be 32–128 URL-safe characters")
    stack = [
        "docker",
        "compose",
        "--project-directory",
        "app/infra",
        "-p",
        "voiceup",
        "-f",
        "app/infra/docker-compose.local.yml",
        "-f",
        "app/infra/docker-compose.observability.yml",
        "exec",
        "-T",
        "postgres",
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "--username",
        "app",
        "--dbname",
        "voiceup_db",
    ]
    # Names are fixed to this product's local role/database. The validated random secret is piped
    # through stdin and is never placed in command arguments or printed in the result.
    sql = f"""
BEGIN;
DO $voiceup$ DECLARE runtime_oid oid; BEGIN
  IF current_database() <> 'voiceup_db' THEN RAISE EXCEPTION 'Unexpected database'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='voiceup_runtime') THEN
    CREATE ROLE voiceup_runtime LOGIN;
  END IF;
  SELECT oid INTO runtime_oid FROM pg_roles WHERE rolname='voiceup_runtime';
  IF EXISTS (SELECT 1 FROM pg_auth_members WHERE member=runtime_oid)
     OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspowner=runtime_oid)
     OR EXISTS (SELECT 1 FROM pg_class WHERE relowner=runtime_oid)
     OR EXISTS (SELECT 1 FROM pg_database WHERE datdba=runtime_oid) THEN
    RAISE EXCEPTION 'Runtime role has unexpected ownership or inherited roles; manual review required';
  END IF;
END $voiceup$;
ALTER ROLE voiceup_runtime PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE voiceup_db TO voiceup_runtime;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO voiceup_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO voiceup_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO voiceup_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE app IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO voiceup_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE app IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO voiceup_runtime;
COMMIT;
"""
    result = subprocess.run(stack, input=sql, text=True, capture_output=True, cwd=root)
    if result.returncode:
        # SQL errors can contain statements; do not echo a password-bearing query.
        raise SystemExit("Local runtime role provisioning failed; check VoiceUp PostgreSQL health")
    if "RUNTIME_DATABASE_PASSWORD" not in configured:
        env_path.write_text(
            source.rstrip() + f"\nRUNTIME_DATABASE_PASSWORD={password}\n", encoding="utf-8"
        )
    print("VoiceUp runtime role provisioned: no superuser, database creation or schema ownership")


def main() -> None:
    try:
        provision_runtime(Path(__file__).resolve().parents[1])
    except ValueError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
