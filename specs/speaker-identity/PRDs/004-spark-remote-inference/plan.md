# Plan — spark-remote-inference

Status: Implemented and live-verified; security release evidence unavailable

Startup extension status: Implemented; one-click service recovery and repeated start live-verified. Cold Docker Desktop startup is automated-test evidence only; no whole-device reboot is claimed.

Authority: [Accepted PRD](PRD.md); evidence: [tasks](tasks.md).

1. Requirement 1 / Decision 3: discover only the user-provided link/host; establish key-based SSH and a known-host record. Add a portable read-only `scripts/inspect-spark.py` and focused tests, and retain private host inventory outside Git.
2. Requirements 2/5 / Decision 4: inspect official ARM64 artifacts, stable version age and driver support. Prepare a separate admitted runtime manifest/lock/image without replacing the working x86_64 profile. Verify actual CUDA and pinned-model output on Spark before any switch.
3. Requirements 3/4: implement the smallest verified SSH/local-Compose transport; test host-loopback reachability from the internal worker network before selecting it. Keep the inference service private and API authentication unchanged.
4. Requirement 6 / Decision 5: add explicit remote startup/config selection, verify a genuine application job, then stop only local inference. Test disconnect, retry, restart and no fallback. Update docs and applicable deploy surfaces together.
5. Run focused tests, model/reference comparison and required quality/config/admission/security gates. Record exact failures and missing hardware/evidence. No success claim for unexecuted remote paths.

Schema/public API/frontend changes are N/A unless discovery changes the accepted PRD first. Existing profile data and user projects are preserved. No Git publishing is inferred from this device request.

Verified transport decision (9 September): a loopback-only Windows nonce server
was reachable from the existing nginx container via Docker's host IPv4, while
the internal worker reported network unreachable. Hostname lookup also failed
under the current restricted DNS configuration. Requirement 4 therefore uses a
separate unpublished nginx listener and explicit Docker host mapping; the worker
remains on its internal network. Spark Docker 29.2.1 does not publish ports from
an internal-only bridge, so a separate relay using the existing admitted nginx
digest joins an edge network and publishes only 127.0.0.1:8090. The model stays
internal-only with no default route. Both relays restrict paths and methods and
preserve authentication, tenant and job headers. See the preflight transport and
runtime service-verification evidence. This choice adds no new application API.

The first real application benchmark exposed intermittent selection of Docker's
unreachable IPv6 host-gateway address. Windows nginx therefore resolves exactly
one canonical IPv4 address from the explicit alias at container startup and
renders only its private upstream into tmpfs. Missing or ambiguous addresses fail
closed; the public server template, read-only image and no-retry POST contract
stay unchanged. Regression verification must exercise multiple nginx workers;
the aborted benchmark remains evidence and is not counted as a performance pass.

Requirements 7/8: add a root Windows click launcher and `scripts/connect-spark.ps1`
to coordinate the existing prepared connection and `start-local.ps1`. Verify the
physical on-link Ethernet route; validate the selected Docker endpoint is local,
start Docker Desktop only when needed, and wait with deadlines. Send the repository's
stdlib `scripts/ensure-spark-runtime.py` over pinned SSH stdin; it validates the
prepared remote service projection and starts only those two services without builds
or pulls. A local single-invocation lock and existing owned-tunnel helpers prevent
duplicate or foreign process cleanup. Verify the public web/API is ready after startup.
No application API, schema, model algorithm or dependencies change. Test failures and
reuse with real local fixtures; exercise the launcher against the running devices,
including stopped project services, then run the full profile gate and record missing
security evidence separately. Daily use assumes the one-time prepared device and keys.

Requirements 7/8 startup regression: after Compose replacement of backend/frontend,
refresh nginx's resolved upstream addresses by validating and reloading its active
Spark configuration. The bounded command runs only in the selected VoiceUp nginx;
private-model readiness precedes reload, while public web/API readiness remains
required by the coordinator. Test wrong/missing active configuration, reload errors
and changed upstream addresses with isolated fixtures. Existing data and services
are not restarted during regression development; the owner run verifies the next
complete one-click startup after the current evaluation finishes.

Requirement 7 stdin regression: specify UTF-8 without a BOM for native process input.
Use ProcessStartInfo.StandardInputEncoding when the runtime exposes it; Windows
PowerShell 5.1 briefly selects the same encoding while creating the pipe and restores
the prior console encoding in finally, including failed process creation. Exercise
UTF-8-with-BOM and OEM 857 consoles in both PowerShell engines using a real child
process and exact input bytes. No interpreter or dependency is added to the launcher.
