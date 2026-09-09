---
name: kt-lab-start
description: Start and verify the existing local KT Rancher/RKE2 LAB and its MCP endpoint.
---

# Start the local KT LAB

Execute the operation; do not only describe commands. This is a runtime operation, not a
provisioning or deployment operation.

## Scope

Start these existing Lima virtual machines in dependency-safe order:

1. `kt-lab-nfs`
2. `kt-lab-server`
3. `kt-lab-agent-1`
4. `kt-lab-agent-2`
5. `kt-lab-mgmt`

Then verify RKE2, Rancher, Harbor, KT Verim and the `kt-scaffold-mcp` service. Ensure the MCP
service is reachable from the Mac at `http://127.0.0.1:18080/mcp`.

## Safety constraints

- Work only with the five VM names above. Never create, edit, delete or factory-reset a VM.
- Never run bootstrap, Helm upgrade, image build/push or database migration commands.
- Never read or print `.local/KV.md`, `~/.kt-verim-lab/lab.env`, kubeconfig contents, tokens,
  passwords, private keys or Kubernetes Secret values.
- Never use `set -x`. Do not change Docker Desktop, Docker Compose or Ollama.
- Treat an already-running component as success; the operation must be idempotent.
- If an unexpected process owns TCP port `18080`, do not kill it. Report its PID and command.
- Keep the user informed while readiness checks are running; use bounded polling rather than one
  long silent wait.

## Procedure

1. Use `/opt/homebrew/bin` on `PATH` and confirm `limactl`, `kubectl` and `curl` exist.
2. Confirm `/opt/homebrew/var/run/socket_vmnet` is a Unix socket. If it is absent, run
   `sudo brew services start socket_vmnet`. If interactive sudo cannot be completed, stop and give
   that exact command to the user; do not switch the VMs to another network mode.
3. Inspect `limactl list`. Confirm all five named VMs already exist, then start only the stopped
   ones in the order above with `limactl start <name>`. A failure for one VM must be reported with
   that VM's status; do not recreate it.
4. Set, without printing file contents:

   ```bash
   export PATH="$HOME/.kt-verim-lab/bin:/opt/homebrew/bin:$PATH"
   export KUBECONFIG="$HOME/.kt-verim-lab/kube/config"
   ```

5. Poll `kubectl get nodes` until the API is reachable and all three RKE2 nodes are `Ready`, with a
   bounded deadline. Show the final node table.
6. Check workload state in `kt-console`, `kt-console-observability` and `kt-scaffold-mcp`. Report
   non-ready pods and recent warning events, but do not mutate workloads.
7. Verify, without `--insecure`, these host endpoints:
   - `https://rancher.lab.internal/ping`
   - `https://harbor.lab.internal/api/v2.0/health`
   - `https://verim.lab.internal`
8. Manage the MCP port-forward in the detached macOS screen session `kt-lab-mcp` so it survives
   the agent shell while retaining the Terminal local-network permission:
   - If `http://127.0.0.1:18080/healthz` is already healthy, preserve the existing listener.
   - If the port is free, close only a stale screen session with that exact name, then start:

     ```bash
     screen -dmS kt-lab-mcp "$HOME/.kt-verim-lab/bin/kubectl" \
       --kubeconfig "$HOME/.kt-verim-lab/kube/config" \
       --namespace kt-scaffold-mcp \
       port-forward service/kt-scaffold-mcp 18080:80
     ```

   - If the port is occupied but the health check fails, inspect the listener and stop without
     replacing or killing it.
   - Poll `/healthz` with a bounded deadline. Then perform an MCP `initialize` request against
     `http://127.0.0.1:18080/mcp`; do not print session identifiers or response headers that are not
     needed for the readiness result.
9. Finish with a compact status table for VMs, RKE2 nodes, Rancher, Harbor, KT Verim and MCP. State
   any failed check honestly. Do not expose credentials.
