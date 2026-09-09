# Closed-network operation

## Operating model

The generated application has no runtime internet dependency. Required wheels, npm cache,
Playwright Chromium tree, OCI images and scanner material enter through the controlled software
supply chain, are admitted by digest and move into the closed environment.

A closed-network claim means more than a local model endpoint. Its scope includes:

- coding-client authentication, telemetry, update and extension behavior;
- model provider/gateway and log-retention policy;
- package-manager index/mirror configuration;
- container-image and workflow-action source;
- browser binary and scanner databases;
- DNS, proxy and egress-denied runner/network-policy evidence.

## Offline bundle

`packaging/offline-bundle.sh` prepares the portable inventory for admission. The generated project's
`scripts/verify-offline-bundle.sh` validates:

- the externally supplied admission digest for `SHA256SUMS`;
- every artifact hash in the internal inventory;
- host platform/architecture compatibility;
- completeness of required Python, npm, browser and image items.

Obtaining the trust anchor and bundle through the same uncontrolled channel weakens the integrity
claim.

## Dependency admission

`dependency-admission.json` binds direct package authorities, OCI digests and workflow actions to
one reviewed inventory digest. A lock change is not automatically admitted; update its
maturity/security/license evidence and rerun quality and security gates.

Package managers are forced into no-index/offline mode. “Download from the internet when absent
from cache” is not part of the closed profile.

## MCP deployment

The Streamable HTTP process runs on `127.0.0.1` beside a gateway sidecar. The gateway supplies:

- OAuth 2.1 identity and scope enforcement;
- TLS or mTLS according to bank policy;
- request/body limits, rate limits and audit identity;
- internal DNS/service discovery.

Tokens and certificates belong to bank-managed runtime secret surfaces, not project files.

## Local-model and client admission

VS Code Local Agent with bank-hosted Ollama/Qwen is the default fully closed profile, but repeat
controlled acceptance tests for every client, model, quantization, context size and hardware
combination. At minimum, measure instruction discovery, tool use, multi-file edits, unit tests,
continuation from repository memory during long tasks and accurate evidence reporting.

A model's advertised large context does not prove that a client uses the same amount effectively or
that session history is durable. Persist long-running task state in PRDs, plans, tasks and repository
manifests.

## Operational records

An admission record includes at least version, platform, model identity, model digest/quantization,
client setting, test scenario, date, result and known limitations. When the UI or model changes,
state which part of prior PoC evidence was rerun.
