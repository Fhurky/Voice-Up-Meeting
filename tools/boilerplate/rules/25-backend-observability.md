---
id: "25-backend-observability"
title: "Keep baseline telemetry useful, bounded, and free of sensitive data"
scope: backend
authority: mandatory
priority: 70
trigger: path-match
applies_to:
  - "app/backend/**"
  - "app/infra/observability/**"
  - "app/devops/charts/app-observability/**"
gate: "backend-test.yml"
---

# Backend observability

The baseline emits structured JSON logs to standard output. Every HTTP completion log contains a
validated or generated request identifier, method, matched route template, response status, and
duration. Raw paths and query parameters are not logged. Return the request identifier as
`x-request-id` so browser, proxy, and backend evidence can be correlated. Never log authorization
headers, JWTs, cookies, request or response bodies, passwords, query strings, tenant records, or
arbitrary exception text.

Health and liveness report only process state. Readiness may check required dependencies but must not
leak connection details. The optional closed observability deployment consists of OpenTelemetry
Collector, Prometheus, Tempo, Loki, and Grafana. It is an infrastructure receiver and investigation
surface, not proof that an application signal exists.

Capability-specific metrics and traces require an accepted PRD that defines the signal name,
attributes, cardinality limit, retention expectation, and a test or dashboard query that consumes
it. Tenant, user, prompt, and business identifiers are forbidden as unbounded metric labels. Do not
claim a dashboard, alert, trace, or SLO is functional until a real application signal reaches its
store and the named query is verified.
