---
id: "51-metrics-before-claims"
title: "Measure before asserting performance, saturation, or root cause"
scope: quality
priority: 60
trigger: on-demand
applies_to:
  - "app/**"
  - "schema/**"
  - "app/devops/**"
  - "plans/**"
  - "specs/**"
gate: "review"
---

# Metrics before claims

Do not assert a bottleneck, saturation, N+1 pattern, exhausted pool, runtime regression, capacity
ceiling, or root cause without reading evidence in the current investigation. Every such statement
cites the metric/query, observed value, time window or timestamp, environment, and whether it is a
peak or steady-state observation. Without that evidence, say the dimension has not been measured.

Measurement discipline:

1. Separate peak, average, percentile, and instantaneous samples. One does not prove another.
2. Separate symptom from cause. Correlation needs a mechanism and evidence that the accused layer
   queued, rejected, or reached its own limit.
3. Check hard failure evidence: status breakdown, error counters, restarts, termination reasons,
   database errors, lock waits, and relevant logs.
4. Distinguish client/proxy transport failures from application responses using server-side data.
5. Treat short rate windows during ramp-up/down as unstable and cross-check the load generator.
6. Compare permission, tenant, cache, request-shape, and deployment variants before generalizing.

Do not recommend more replicas, a larger database, a pool change, an index, or a cache as a fix until
measurements show that layer is limiting the objective. Record the query so another person can repeat
the observation.
