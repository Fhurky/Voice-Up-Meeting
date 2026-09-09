---
name: kt-lab-stop
description: Stop the local KT Rancher/RKE2 LAB safely and release its VM resources.
---

# Stop the local KT LAB

Execute the operation; do not only describe commands. Stop runtime resources without deleting the
LAB or changing its configuration.

## Scope

Stop the MCP port-forward and these existing Lima virtual machines in shutdown order:

1. `kt-lab-agent-1`
2. `kt-lab-agent-2`
3. `kt-lab-server`
4. `kt-lab-mgmt`
5. `kt-lab-nfs`

## Safety constraints

- Work only with the five VM names above.
- Use only graceful `limactl stop <name>` operations. Never use `limactl delete`, disk removal,
  factory reset, forced process killing or recursive deletion.
- Never read or print `.local/KV.md`, `~/.kt-verim-lab/lab.env`, kubeconfig contents, tokens,
  passwords, private keys or Kubernetes Secret values.
- Never stop Docker Desktop, Docker Compose, Ollama or unrelated Lima instances.
- Leave `socket_vmnet` running: its idle footprint is negligible and stopping the shared root
  service can affect unrelated Lima instances.
- Treat an already-stopped component as success; the operation must be idempotent.

## Procedure

1. Inspect the detached macOS screen session `kt-lab-mcp`. If it exists, stop only that exact
   session with `screen -S kt-lab-mcp -X quit`.
2. If TCP port `18080` still listens afterward, inspect the owning process. Stop it only when it
   belongs to the current user and its command line is the exact `kubectl` port-forward for
   namespace `kt-scaffold-mcp`, service `kt-scaffold-mcp` and mapping `18080:80`. Otherwise preserve
   it and report the conflict.
3. Inspect `limactl list`. Stop only running instances from the scope, sequentially in the shutdown
   order above. Report a stop failure; never delete or recreate an instance.
4. Poll with a bounded deadline until all five scoped VMs report `Stopped`.
5. Verify that the managed MCP listener is gone when it was owned by this LAB. Do not treat an
   unrelated preserved listener as successful cleanup.
6. Finish with a compact VM table and state that the LAB's virtual-machine CPU and memory have been
   released. List any VM, `kt-lab-mcp` screen session or managed port-forward that remains running.
   Do not expose credentials.
