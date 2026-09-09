# Run report — 2026-09-09 · private inference HTTP, audio and offline model package

1. Result: Inference implementation and real CUDA HTTP verification passed — unit 36 passed / real GPU integration 12 passed / browser 0 passed / skipped 0; awaiting decision: none.
2. Ran: Isolated Windows CPython 3.13 — `tests/test_service.py`: 21 tests; `tests/test_bundle.py`: 7 tests; `tests/test_wheelhouse.py`: 8 tests. Ruff 0.16.1 and the real model package verifier passed. The image installed all 62 hash-locked wheels with `--no-index --require-hashes` in a Docker `--network=none` build step. A separate read-only, network-none container ran Python 3.13.14, torch 2.8.0+cu128 / CUDA 12.8 on the real NVIDIA GeForce RTX 4060 Laptop GPU. All 12 production HTTP checks passed. The Compose service is running and healthy. Earlier explicit CPU adapter/fixture checks used the existing Python 3.12 reference environment with socket connections blocked; those results are separate from the CUDA evidence.
3. Items:
   **DEFECT**
   M1 The initial multi-index lock selected stale unrelated CUDA-index packages; fixed by resolving with `--torch-backend cu128`, then hash-enforced installation with fixed versions.
   M2 Invalid short secrets appeared in Pydantic validation messages; a failing regression test preceded `hide_input_in_errors=True` and sanitized bootstrap error handling.
   M3 The first connected Docker build downloaded CUDA dependencies but then could not resolve torch. The emitted `--index-url` in the requirements file reset pip's command-line index list. Regenerating without `--emit-index-url` preserves all package pins/hashes and fixes that configuration error. Logs: `evidence/first-build-failure.log`. The official index's R2 host additionally returned HTTP 403 for the selected CUDA wheels; the canonical official hostname works with identical pinned hashes. Triton must use its locked PyTorch-index artifact, not a differently hashed PyPI build. A persistent verified wheelhouse is used for the retry.
   **TRAP**
   M4 Unit HTTP tests use deterministic model doubles; the later GPU integration checks load the actual pinned ECAPA and Silero files. Repeating public clips proves software wiring and is not held-out speaker accuracy evidence.
   M5 Starlette/httpx, AnyIO and the pinned torchaudio backend API emitted deprecation warnings; checks pass without suppressing warnings. The optional connected Dockerfile has not passed in this network; Compose defaults to the verified offline path.
   **OBSERVATION**
   M6 The model package contains only the pinned ECAPA and Silero files; a manifest cannot replace the compiled content-hash allowlist. The isolated GPU container returned `/live` and `/ready` 200; malformed WAV 400; unsupported bytes 415; bad key 401; silence 422; and six successful WAV/FLAC enrollment/identification requests with 192-dimensional unit-normalized embeddings. Raw vectors and keys are absent from recorded evidence.
   M7 First constructed 30-second enrollment HTTP took 0.675 s after readiness warmup; later fixture requests took 0.610–0.710 s. Peak PyTorch allocated bytes were 188,786,688–199,446,016; maximum reserved bytes were 272,629,760. These are process allocator figures including resident models, not whole-device VRAM or a 20-job queue benchmark. Compose process start to application readiness was 4.909 s; first successful readiness log was at 5.380 s, including probe scheduling. Container creation/image build are excluded and the host page cache was warm. The isolated in-process HTTP startup was 3.415 s excluding initial Python imports.
   **OPEN**
   M8 Separate-session user recordings are unavailable; Turkish speaker-recognition accuracy is unmeasured. The parent task owns the browser/public API and 20-job latency benchmark; the private HTTP timings above do not establish those results.
   M9 The bank's artifact transfer, target machine and Kubernetes deployment environment have not been supplied or tested by this service task. The local runtime smoke had no external network interface; the offline package-install step had networking disabled. This does not claim registry metadata resolution by the build host was disconnected.
   **SIDE-EFFECT**
   M10 Created standalone inference source/tests, runtime and test dependency locks, online/offline Dockerfiles, packaging/wheelhouse/smoke commands, verification evidence, ignored local model/wheel caches, the local image and the running Compose inference service. The root CPU environment was unchanged.

Reproducible provisioning on the connected build host, from the repository root:

```sh
uv run --no-project --python 3.13 --with 'packaging==26.3' \
  python app/inference/provision_wheelhouse.py \
  --destination models/inference-wheelhouse --workers 8
```

After the complete wheelhouse verifies, the offline build and local Compose tag:

```sh
docker build --network=none \
  --build-context wheelhouse=/absolute/path/VoiceUpMeating/models/inference-wheelhouse \
  -f app/inference/Dockerfile.offline -t voiceup-inference:pilot .
docker tag voiceup-inference:pilot voiceup-inference:latest
sh scripts/stack.sh up -d --no-build --no-deps inference
```

The target needs the digest-pinned Python base image already cached. These commands
do not establish that the bank's artifact transfer or deployment environment has
been tested. The successful local build log is `evidence/offline-build.log`; wheel
verification metadata is `evidence/wheelhouse-verification.json`.

The actual isolated GPU test used this command from the repository root (replace
the absolute paths for another host):

```sh
docker run --rm --gpus all --network=none --read-only \
  --tmpfs /tmp:rw,size=536870912,mode=1777 --env HOME=/tmp \
  --mount type=bind,source=/absolute/VoiceUpMeating/models/speaker-pilot,target=/models/speaker,readonly \
  --mount type=bind,source=/absolute/VoiceUpMeating/app/inference/smoke_cuda.py,target=/checks/smoke_cuda.py,readonly \
  --mount type=bind,source=/absolute/VoiceUpMeating/outputs/live-browser,target=/fixtures,readonly \
  voiceup-inference:pilot python /checks/smoke_cuda.py \
  /fixtures/repeated-public-sample-30s.wav \
  /fixtures/repeated-other-public-sample-30s.wav
```

`evidence/cuda-smoke.json` records the 12 checks, model revision, device, timing and
allocator measurements. `evidence/cuda-smoke-stderr.log` preserves library warnings.
`evidence/compose-startup.json` records the Docker timestamps and timing scope.
The fixture definitions and hashes are maintained by the frontend task in
`outputs/live-browser/fixture.json` and `other-fixture.json`.
