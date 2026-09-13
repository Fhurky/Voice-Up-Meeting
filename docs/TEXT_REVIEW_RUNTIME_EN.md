# Local text model connection

This optional feature keeps the `kt-vibecoding-python-web-v2` FastAPI boundary
and uses an already installed Ollama model. It neither downloads models nor
changes the ASR/speaker runtime mode.

When updating an existing installation to saved corrections, first apply the
additive migration to the running local PostgreSQL before restarting the backend:

```sh
sh scripts/db.sh apply
sh scripts/db.sh validate
sh scripts/db.sh status
```

This release's schema head is `8283cb0d9e4b`. Original transcripts remain intact;
corrections use a separate table. In a cluster, use the migration release step;
do not apply a cluster database migration from a developer workstation.

With Ollama running on the computer, use an existing Python from the project root:

```sh
python3 scripts/setup-local-text-review.py --check --model qwen3.5:27b
python3 scripts/setup-local-text-review.py --enable --model qwen3.5:27b
sh scripts/stack.sh up -d --no-deps --no-build --pull never nginx backend
sh scripts/stack.sh restart backend
```

On Windows, use `python` and the installed Git Bash for the shell commands, or
run `scripts/start-local.ps1` after setup. Existing GPU, CPU and Spark selections
are retained. The final restart also reloads nginx's active configuration and
its backend address. No model is downloaded. The helper pins the installation's
default model. After replacing that model's files, run enable again to pin its
new digest; there is no automatic fallback. Other installed models can be selected
per request in the review panel without changing the default setting.
To disable, run `python3 scripts/setup-local-text-review.py --disable` and the same
refresh commands. The installed model and unrelated local settings are preserved.

The helper reads only loopback `127.0.0.1:11434` metadata, rejects remote/cloud
model indicators, and pins the selected SHA-256 identity. It updates only
`TEXT_REVIEW_*` assignments in ignored `app/infra/.env` and the optional
`outputs/local-text-review-enabled.txt` marker; it does not print secrets.

| Application setting | Default | Meaning |
|---|---|---|
| `VOICEUP_TEXT_REVIEW_ENABLED` | `false` | Enable the optional preview. |
| `VOICEUP_TEXT_REVIEW_URL` | `http://nginx:9081` | Operator-selected model service origin. |
| `VOICEUP_TEXT_REVIEW_MODEL` | `qwen3.5:27b` | Pinned default model for the installation. |
| `VOICEUP_TEXT_REVIEW_MODEL_DIGEST` | empty | Required 64 lowercase hexadecimal SHA-256 characters when enabled. |

Docker listener 9081 is unpublished. It forwards only `/api/tags`, `/api/show`
and `/api/chat` using their required methods. Pull/create/delete routes remain
closed. Only the existing nginx joins the host-facing network; application/data
services remain internal. Spark's separate private 9080 listener is composed
into the same active configuration. Ollama's localhost binding, firewall and
internet-egress policy are unchanged.

The local public nginx waits 110 seconds for the correction-preview and correction-suggestion paths;
the application deadline remains 100 seconds and the client deadline 120 seconds.
Other local API timeouts remain unchanged. This avoids terminating a valid slow
application response before its own deadline; it does not speed up the model.

Docker Desktop host-loopback forwarding is required. Windows Docker Desktop was
observed; macOS/native Linux device verification remains separate. Native Linux
host-gateway access to a loopback-only service is not assumed. A connection
failure leaves the original transcript usable; setup does not expose Ollama to LAN.

For Kubernetes, prepare an existing on-premise Ollama service in the same
namespace and label its pod `app.kubernetes.io/part-of: voiceup` and
`app.kubernetes.io/component: text-review`. Set `textReview.enabled: true` in
the environment `platform.yaml`; this adds only TCP 11434 egress to that pod
selector. No other namespace/IP or internet rule is admitted. The model workload
owner supplies its ingress policy.

When enabled, the existing backend Ingress receives a 110-second read-timeout
annotation. Its scope covers that Ingress's `/api` paths, unlike the narrower
local path rule. Existing `Prefix` matching is preserved with no regex/snippet.
An ingress-nginx `use-regex` annotation would affect every path on the same host,
so a separate regex route is avoided. [Controller documentation](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/#use-regex).

Supply all four `VOICEUP_TEXT_REVIEW_*` values through the backend's single
pre-created `existingSecret`. Use the internal model service URL rather than the
local Docker nginx address. Never put Secret contents in chart values or overlays.
Configure both the network selection and application enable setting together.
Model installation remains an external prerequisite; no image or dependency is added.

[Türkçe](TEXT_REVIEW_RUNTIME.md)
