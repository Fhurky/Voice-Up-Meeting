# PRD — Secure tenant-aware web baseline

Status: Draft

Document version: 0.1.0

Domain: [Application Foundation](../../DOMAIN.md)

Roadmap: [Capability 001](../../roadmap.md)

## Intent

Ensure every separated-web scaffold begins with a small but real security and application foundation:
FastAPI health and authentication, PostgreSQL desired state, JWT access tokens, tenant context, RBAC,
an application-level super administrator, a React login/session shell, and an executable browser login
scenario—without inventing business-domain code.

This is a retrospective Draft. Existing generated templates are observed baseline and require owner
acceptance plus fresh generated-project evidence.

## Actors and outcomes

- An application developer can boot a new project, apply its baseline migration, create the first
  administrator, sign in, and reach a protected UI before implementing a business capability.
- An ordinary user is constrained by token identity, active tenant, and permission checks.
- An application super administrator can perform application-wide administration without receiving OS,
  database-superuser, container-root, or cluster-admin authority.
- A security reviewer can trace the same identity and tenant contract through schema, backend, frontend,
  and browser behavior.
- A product team receives no sample `item`, CRUD route, or fake business success response.

## Verified baseline and gap

The generated Python/FastAPI template contains tenant, user, role, and permission models; JWT login and
`/auth/me`; request and tenant context; permission dependencies; an idempotent super-admin bootstrap;
structured request logging; health behavior; SQLAlchemy/Alembic desired state; and unit/integration
tests. The React/Vite template contains token storage, typed authentication service, auth context,
protected/permission routes, login page, and localized catalogs. The browser harness includes a
super-admin login scenario.

Current gaps include owner-approved token/session lifecycle, explicit brute-force/rate-limit boundary,
complete negative tenant lifecycle evidence, production identity integration policy, password-reset and
revocation scope, and a fresh L2 run against the current generated tree and admitted artifacts.

## Decisions, invariants, and trust boundaries

1. Authentication uses signed JWT access tokens and authorization uses RBAC with one application-level
   `super_admin` bypass.
2. Application super-admin is not operating-system root, container root, database superuser, Kubernetes
   administrator, or enterprise identity administrator.
3. The active tenant comes from the configured request header and must agree with principal authority.
4. Tenant-scoped queries require active, non-deleted tenant and non-deleted record state.
5. Production signing secrets have no fallback and must meet configured strength and algorithm rules.
6. Bootstrap credentials enter through protected runtime input, never process arguments, answers,
   examples, logs, or version control.
7. Browser and frontend storage behavior is part of the security contract and must match backend token
   semantics.
8. Baseline authentication is platform behavior; product-specific users, roles, approvals, SSO, MFA, and
   workflows require accepted capabilities or organization integration.
9. The baseline contains no business aggregate or generic CRUD generator output.

## Functional requirements

1. A fresh migration must create tenant, user, role, permission, and association authority with required
   audit, public-ID, lifecycle, and integrity fields.
2. Login must validate credentials without leaking which identity field failed and return the shared
   typed token contract.
3. `/auth/me` must return the authenticated principal, roles/permissions, and effective tenant context.
4. Request context must carry a bounded request ID and active tenant and must not trust arbitrary tenant
   switching by ordinary users.
5. Permission guards must use validated `resource:action` identifiers and default protected behavior.
6. Super-admin may bypass application permission checks and switch application tenant context only.
7. Bootstrap must be idempotent, create or reconcile the application super-admin safely, and read the
   password through standard input or an equivalent protected channel.
8. Configuration must reject missing/weak JWT secrets and unsupported algorithms outside explicit test
   fixtures.
9. The frontend must restore/clear session consistently, attach the token through the shared API client,
   fetch the current principal, and protect routes before rendering protected content.
10. Login, loading, authentication failure, authorization failure, and session expiry behavior must be
    localized and testable.
11. OpenAPI and generated frontend types must remain synchronized with backend authentication contracts.
12. Structured request logs must include request ID, method, normalized path, status, and duration while
    excluding token, credentials, headers, query, and body data.
13. Health behavior must distinguish process liveness and dependency readiness where deployment relies on
    that distinction.

## Security and authorization

- Password hashing, token creation/validation, algorithm allow-list, expiry, clock behavior, and error
  semantics require focused tests.
- Authorization checks must occur server-side; frontend guards are user experience controls only.
- Tenant identity must be enforced in repositories and not only in middleware or endpoint code.
- Runtime containers and database connections remain non-root/non-superuser.
- Rate limiting, credential-stuffing defense, enterprise identity federation, refresh tokens, revocation,
  MFA, and account recovery require an explicit owning boundary before production use.
- Security logging must not disclose passwords, tokens, full headers, or personal data.

## Data and migration

- SQLAlchemy desired state is authoritative and Alembic migration history must match it.
- Authentication records use internal numeric keys and stable public identifiers where exposed.
- Tenant/user deletion and deactivation semantics must prevent later data access by otherwise valid
  tokens.
- Baseline seed/bootstrap must be repeatable and must not store a default production credential.
- Backward-incompatible claim or schema changes require migration and session invalidation policy.

## Validation, observability, and evidence

- L1 covers configuration failure, password hashing, token validation, login, `/auth/me`, permission
  checks, super-admin bypass, tenant mismatch, inactive/deleted tenant, migration, bootstrap idempotency,
  frontend storage/context/route behavior, OpenAPI drift, and secret-free logging.
- L2 starts the real local stack, applies the migration, bootstraps a super-admin, signs in through the
  browser, confirms JWT-backed `/auth/me`, active tenant, protected route access, and relevant failure
  behavior through loopback Nginx.
- Security scanner and dependency results are supporting evidence, not authentication behavior proof.
- L3 requires an accountable owner to accept representative identity and tenant behavior.

## Risks and open questions

- Is access-token-only authentication sufficient for the first supported production profile?
- Which component owns rate limiting, lockout, MFA, SSO, refresh/revocation, and account recovery?
- What token lifetime and clock-skew policy is approved?
- How are tenant suspension and user revocation reflected before an issued token expires?
- Which authentication events enter the organization audit system and under what retention policy?

## Acceptance criteria

- [ ] The security and product owners accept the baseline identity, tenant, and super-admin boundaries.
- [ ] A fresh desired state and migration create the full baseline with no default production secret.
- [ ] Missing/weak secrets, unsupported algorithms, invalid/expired tokens, and malformed tenant context
  fail closed.
- [ ] Ordinary users cannot cross tenant or permission boundaries, including after tenant deactivation or
  soft deletion.
- [ ] Application super-admin behavior works without infrastructure privilege escalation.
- [ ] Bootstrap is idempotent and its password is absent from arguments, files, manifests, and logs.
- [ ] Backend OpenAPI and frontend types/session behavior remain synchronized.
- [ ] Structured logs contain required request metadata and exclude sensitive content.
- [ ] The real browser login, `/auth/me`, tenant, and protected-route path passes against PostgreSQL.
- [ ] Documentation lists excluded identity capabilities and their owning future decisions.

## Delivery flow

Draft -> security/product review -> Accepted -> implementation reconciliation -> schema/backend/frontend
tests -> real stack and browser evidence -> owner acceptance -> staged template release
