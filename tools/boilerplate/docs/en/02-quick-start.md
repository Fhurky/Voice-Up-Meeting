# Quick start

This flow uses the local CLI to generate a deterministic project, create its first PRD and show the
boundary through quality evidence. Run the commands with your organization's approved
Python/wheel/OCI distribution; do not reach a public package index from the closed network.

## 1. Verify the CLI

A boilerplate contributor can use this development environment in the repository:

~~~sh
python3.13 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/kt-scaffold --version
~~~

Project users should instead use the pinned `kt-scaffold` wheel or OCI package admitted through the
bank's software supply chain. Python 3.13 is required.

## 2. Generate a project from an empty directory

~~~sh
kt-scaffold init \
  --target-dir ./payment-reconciliation \
  --intent "Build an internal payment reconciliation service" \
  --primary-domain payments \
  --product-name "Payment Reconciliation"
cd payment-reconciliation
~~~

`init` resolves the fixed Python/FastAPI and SQLAlchemy/Alembic profile; it offers no alternative
backend selection. The result JSON reports changed files and next steps. Key outputs include:

- `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`, `.cursor/` — client projections;
- `specs/payments/` — domain context, roadmap and PRD area;
- `app/backend/`, `app/frontend/`, `schema/` — fixed application profile;
- `scripts/` — bootstrap, database, drift, security, E2E and quality entry points;
- `.kt-scaffold/` — answers, managed state, bounded project manifest and evidence records.

Review the product name, intent, domain and `technology-profile.yml` values before committing.

## 3. Run the platform baseline

The generated `README.md` and your organization's approved offline-bundle record are authoritative.
The baseline sequence is:

~~~sh
scripts/bootstrap.sh
scripts/stack.sh up -d --build --wait
scripts/db.sh apply
scripts/create-super-admin.sh
scripts/quality-gate.sh all
~~~

For browser E2E, supply the approved bundle path and the admission digest for `SHA256SUMS`, then run:

~~~sh
export KT_SCAFFOLD_OFFLINE_BUNDLE=/approved/bundles/<platform-matrix>
export KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-sha256-of-SHA256SUMS>
scripts/e2e.sh auth
~~~

Do not commit these values. The bank environment supplies the real paths and digests.

## 4. Define the first business capability

~~~sh
kt-scaffold spec \
  --target-dir . \
  --domain payments \
  --capability transaction-search \
  --intent "Let an authorized operator find reconciliation transactions" \
  --mode comprehensive
~~~

The command returns `spec_path`; in this example it is
`specs/payments/PRDs/001-transaction-search/PRD.md`. Complete the actors, boundaries, security and
data impact, and acceptance criteria. After human review, change only `Status: Draft` to
`Status: Accepted`. That status authorizes business-code generation; an agent should not make the
acceptance decision by itself.

`plan.md` should map each affected layer to acceptance criteria, while `tasks.md` names checkable
outputs. Preserve the `Spec → Plan → Tasks → Implement` order.

## 5. Prepare a vertical slice from the accepted PRD

~~~sh
SPEC_PATH=specs/payments/PRDs/001-transaction-search/PRD.md

kt-scaffold domain --target-dir . --spec-path "$SPEC_PATH" \
  --permission read=transaction_search:read
kt-scaffold schema --target-dir . --spec-path "$SPEC_PATH" \
  --change-summary "Add transaction search desired state" \
  --migration-name add-transaction-search
kt-scaffold page --target-dir . --spec-path "$SPEC_PATH" \
  --page transaction-search --route /transaction-search \
  --permission transaction_search:read
kt-scaffold scenario --target-dir . --spec-path "$SPEC_PATH" \
  --suite payments --scenario-title "Authorized transaction search" \
  --acceptance-point "Authorized operator sees matching transactions"
~~~

These commands do not claim a completed feature. In particular, the browser scenario does not
treat acceptance prose as an executable test and deliberately fails until real assertions replace
its guard. Complete the generated structure from the PRD, plan and tasks.

## 6. Produce quality and delivery evidence

You can run the repository-owned gate directly:

~~~sh
scripts/quality-gate.sh all --include-browser
~~~

When the CLI invokes the same gate, you must explicitly confirm trust in the target repository's
project-owned script:

~~~sh
kt-scaffold gate --target-dir . --scope all --include-browser \
  --allow-project-code-execution
kt-scaffold done --target-dir . \
  --change-summary "Deliver transaction search vertical slice" \
  --claimed-tier L2
~~~

`done` does not approve a tier unsupported by recorded evidence. L3 additionally requires product
owner acceptance with representative real data.

## Where does MCP fit?

Trusted local stdio MCP provides deterministic `project_create`; the HTTP MCP provides
`project_blueprint` and workspace-blind governance operations. Neither asks a model to recreate the
scaffold or downloads executable code. Local stdio and CLI creation must produce the same digest.
For the boundary and configuration, see
the [Global MCP scaffolding and governance plane](../global-mcp.md).
