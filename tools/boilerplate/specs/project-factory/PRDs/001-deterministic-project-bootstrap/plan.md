# Plan — Deterministic project bootstrap

Status: Active

Derived from the [Accepted PRD](PRD.md).

1. Replace MCP-delivered executable application with an installed local stdio creation boundary.
   Requirements 3, 4, 7–10.
2. Persist validated Agent Platform client selection and replay it through init/update rendering.
   Requirements 1, 5, 11.
3. Add strict workspace binding, idempotent completed retry and local observed receipts.
   Requirements 2–4, 6–8.
4. Retain the HTTP server as a workspace-independent governance surface and remove executable
   applicator discovery/delivery. Requirements 9, 10, 12.
5. Verify focused contracts, full repository gates, real stdio MCP creation, HTTP negative discovery
   and the Rancher/RKE2 deployment boundary. Acceptance criteria 2–8.

No step authorizes runtime admission of an Agent Platform client projection.
