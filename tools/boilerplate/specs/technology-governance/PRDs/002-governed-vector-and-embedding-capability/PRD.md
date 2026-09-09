# PRD — Governed vector and embedding capability

Status: Draft

Document version: 0.1.0

Domain: [Technology Governance](../../DOMAIN.md)

Roadmap: [Capability 002](../../roadmap.md)

## Intent

Permit application teams to implement reviewed vector search and embedding-backed capabilities inside
the fixed PostgreSQL boundary while preventing ungoverned vector databases, runtime model download,
provider ambiguity, mixed embedding spaces, unsafe tenant search, or prose-only quality claims.

This retrospective Draft records policy/profile enablement. It does not activate PGVector in a generated
project, select a provider/model, implement a retrieval feature, or claim runtime conformance.

## Actors and outcomes

- A product owner can request an embedding-backed actor outcome with measurable retrieval quality and
  latency.
- An application developer gets one approved persistence and adapter boundary rather than selecting an
  external vector database.
- A data/security reviewer can evaluate source classification, minimization, retention, model identity,
  and tenant isolation before data is embedded.
- A database reviewer can approve extension activation, index strategy, query shape, migration, and
  rollback.
- An evidence reviewer can distinguish allowed capability, project activation, data backfill, and live
  retrieval quality.

## Verified baseline and gap

The current technology profile allows PGVector only in the same PostgreSQL database, requires a reviewed
Alembic migration, fixes a minimum extension version, allows exact/HNSW/IVFFlat search with a controlled
metric set, and forbids an alternative vector database. Embedding generation must sit behind an
application port with approved internal/on-premise adapter, no runtime egress or model download. The PRD
template requires provider, immutable model identity, dimensions, normalization, metric, index strategy,
quality/latency thresholds, and re-embedding behavior. Storage rules require model/source/content
identity and tenant-qualified similarity search.

The repository does not currently implement a business vector capability, migration, provider adapter,
model runtime, evaluation dataset, recall/latency result, re-embedding job, or live tenant-isolation
proof. Those remain capability-specific work.

## Decisions, invariants, and trust boundaries

1. PGVector is a PostgreSQL extension and reviewed capability, not a separate persistence engine.
2. Alternative vector databases are forbidden by the current profile.
3. Extension activation requires an accepted business PRD and reviewed Alembic migration.
4. Embedding generation crosses an application port into an approved internal or on-premise adapter.
5. Runtime internet egress and runtime model download are forbidden.
6. Model ID/version, dimensions, normalization, metric, and index strategy are immutable search-space
   identity and must remain aligned.
7. Every stored vector binds source identity, content hash, model identity, and tenant scope.
8. Similarity queries are tenant qualified and must obey source authorization, lifecycle, and retention.
9. Mixed-model search is forbidden; upgrades use versioned backfill, validation, and cutover.
10. Retrieval quality and latency are observed against a named evaluation set; provider/model marketing
    claims are not evidence.

## Functional requirements

1. An activating business PRD must declare provider/deployment boundary, immutable model ID/version,
   dimensions, normalization, distance metric, index/search strategy, quality and latency thresholds,
   source classification/minimization/retention, and re-embedding/cutover/rollback.
2. The provider adapter must expose a project-owned application port and must not leak provider types,
   endpoints, or credentials into the domain model.
3. Model artifacts must enter through Delivery Assurance admission with digest, license, provenance,
   platform compatibility, and security evidence.
4. The reviewed migration must install/verify the required PGVector extension and create fixed-dimension
   columns and indexes matching the accepted contract.
5. Persisted embeddings must record source identity, source version or content hash, model identity,
   dimensions, lifecycle/cutover state, timestamps, and tenant ownership.
6. Ingestion must apply classification, minimization, chunking, authorization, deletion, and retention
   before or with embedding generation.
7. Similarity queries must include tenant/source authorization and active/non-deleted predicates before
   ranking or result return.
8. Query construction must match metric and index operator class and provide a reviewed exact-search
   validation path where applicable.
9. Re-embedding must write a separate versioned space, validate coverage/quality, cut over atomically,
   prevent mixed search, and retain a bounded rollback window.
10. Destructive rebuild or old-vector deletion requires explicit authorization and retention checks.
11. Runtime configuration must fail closed on missing/mismatched provider, model identity, dimensions,
    normalization, or metric.
12. Observability must record bounded latency, error, queue/backfill progress, model identity, and quality
    evaluation metadata without source content or embeddings.

## Security and authorization

- Source authorization applies before embedding and again before retrieval result disclosure.
- Sensitive data requires documented classification, minimization, retention, deletion propagation, and
  provider-processing boundary.
- Embeddings are treated as derived sensitive data according to source classification and threat model.
- Provider credentials/endpoints remain runtime secret/configuration and are absent from portable PRDs,
  source artifacts, logs, and model-visible output.
- Tenant isolation must be proven at SQL query and integration-test level, not only application filters.
- Prompt injection and retrieval poisoning controls belong to the consuming business capability and
  Agent Platform/tool boundary where applicable.

## Data and migration

- PGVector activation and vector column/index changes use reviewed Alembic history against disposable
  PostgreSQL validation.
- Model/dimension/normalization/metric changes create a new embedding version; in-place reinterpretation
  is forbidden.
- Source update/deletion must invalidate or delete derived chunks/vectors according to accepted policy.
- Backfill is resumable, observable, tenant-safe, and idempotent by source/content/model identity.
- Rollback and retention define when old vectors may be queried, retained, or destroyed.

## Validation, observability, and evidence

- L1 covers profile/schema validation, accepted-PRD field completeness, extension migration, dimension
  enforcement, adapter boundary, tenant/source predicates, metric/operator alignment, model identity,
  mixed-version rejection, deletion propagation, and re-embedding state transitions.
- L2 runs the admitted provider/model and PostgreSQL extension with representative authorized/unauthorized
  tenants, observed recall/quality dataset, latency percentiles, failure behavior, backfill, cutover, and
  rollback.
- Evidence records provider deployment, model digest/version, dimensions, metric/index, PostgreSQL and
  extension versions, dataset identity, thresholds, results, and date.
- Model discovery or successful `/models` response is not embedding or retrieval conformance.

## Risks and open questions

- Which internal/on-premise provider and immutable model are initially admitted?
- What evaluation dataset and relevance judgments define the quality threshold?
- Which source classifications are allowed, and how are deletion/retention obligations propagated?
- When are HNSW or IVFFlat justified over exact search, and who approves tuning/maintenance?
- What backfill throughput, resource, failure-retry, and cutover window is acceptable?

## Acceptance criteria

- [ ] Product, data, security, database, and platform owners accept the activating PRD contract.
- [ ] The fixed profile rejects alternative vector databases and activation without an accepted PRD.
- [ ] Provider/model artifacts are digest-admitted and run without public egress or model download.
- [ ] A reviewed migration activates the approved PGVector version and fixed-dimension schema/index.
- [ ] Storage and similarity queries bind tenant, source, content, model, dimensions, metric, and lifecycle.
- [ ] Negative tests prove cross-tenant, deleted/inactive source, mixed-model, dimension mismatch, and
  metric/index mismatch fail closed.
- [ ] Re-embedding backfill, validation, atomic cutover, rollback, and destructive cleanup controls pass.
- [ ] Representative live evaluation meets accepted retrieval-quality and latency thresholds.
- [ ] Sensitive source and derived-vector classification, minimization, retention, and deletion are
  evidenced.
- [ ] Documentation distinguishes allowed profile capability, project activation, runtime conformance,
  and production acceptance.

## Delivery flow

Draft -> product/data/security/database review -> Accepted activating PRD -> provider/model admission ->
migration and adapter plan -> unit/integration evidence -> backfill and live quality evaluation -> staged
cutover -> periodic revalidation
