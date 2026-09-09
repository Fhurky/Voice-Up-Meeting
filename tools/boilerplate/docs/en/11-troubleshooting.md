# Troubleshooting

| Symptom | Likely cause | Safe check / resolution |
|---|---|---|
| A project command cannot find the project root | Wrong directory or missing `.kt-scaffold` manifest | Give an explicit `--target-dir`; verify `.kt-scaffold/answers.yml` exists |
| `domain`, `page`, `schema` or `scenario` rejects a PRD | Wrong path or PRD is still Draft | Verify the `spec_path` shape and exact `Status: Accepted` line as a human decision |
| `update` returns a conflict | A user changed a managed file | Do not overwrite; semantically merge canonical behavior with the accepted product need |
| `render --mode check` fails | A client projection drifted from source rules | Validate the `rules/` source change, then run `render --mode write` and drift check |
| `gate` refuses project-code execution | Explicit trust confirmation is missing | Inspect the target repository and diff; pass `--allow-project-code-execution` only if trusted |
| Exit code is 0 but no gate evidence is created | `KT_GATE_*` step/test lines are absent or inconsistent | Fix the project-owned script; do not treat exit code alone as evidence |
| Browser E2E fails immediately | The generated failing guard has not been replaced by assertions | Add assertions validating the acceptance point through the real UI |
| Offline bundle does not verify | Incomplete bundle, wrong platform or admission-digest mismatch | Re-obtain bundle and trust anchor through the approved channel; do not bypass the check |
| Streamable HTTP cannot bind non-loopback | Direct external listeners are rejected by policy | Run MCP on loopback and expose it through the bank gateway sidecar |
| `project_create` is unavailable | The client uses HTTP governance or local stdio lacks `--workspace-root` | Register trusted local stdio against the explicit open workspace |
| Local creation is rejected | Root is unsafe, symlinked, unowned/non-empty, partial or edited | Preserve the target; retry with the exact completed scaffold or a new empty directory |
| MCP update does not see every local change | Only bounded project manifest metadata is sent | Have the agent compare artifact proposals with the local diff; do not send source to MCP |
| A new agent session lost context | The decision existed only in chat history | Update PRD/plan/tasks, decision log and manifest; have the new session read them |
| A local model handles small code but drifts in long tasks | Weak context management, model size/quantization or repository memory | Split work into accepted tasks; rerun the same admission matrix for the model/hardware combination |

## Diagnostic order

1. Read the worktree and target directory; preserve user changes.
2. Record the generator version with `kt-scaffold --version`.
3. Check `technology-profile.yml` and `.kt-scaffold/answers.yml` consistency.
4. Run `python3 scripts/check-governance-drift.py` and `python3 scripts/check-config-sync.py`.
5. Reproduce with the narrowest CLI command or test.
6. Report the command, exit code, stable evidence lines and environment limitation together.

Do not copy secrets, customer data or closed-network addresses into an issue. Use a redacted,
reproducible fixture when needed.
