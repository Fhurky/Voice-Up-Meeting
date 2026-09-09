# Private speaker inference service

Implements the Accepted local-speaker pilot under the fixed
`kt-vibecoding-python-web-v2` technology profile. This service is internal HTTP only,
does not access PostgreSQL, and exposes no user or profile management API.

## Runtime and model boundary

The image uses digest-pinned Python 3.13.14 on Debian Bookworm. PyTorch
2.8.0+cu128 and torchaudio 2.8.0+cu128 supply the CUDA userspace dependencies;
the host must expose its NVIDIA device through the container runtime. Official
CPython 3.13 Linux x86-64 wheels are listed in the [torch index](https://download.pytorch.org/whl/cu128/torch/)
and [torchaudio index](https://download.pytorch.org/whl/cu128/torchaudio/), and the pair
is documented for CUDA 12.8 in [PyTorch's version instructions](https://pytorch.org/get-started/previous-versions/).
Sources checked 9 September 2026. Wheel availability is compatibility evidence;
successful model execution on the target GPU must be established separately.

`requirements.in` is the candidate dependency authority and `requirements.txt`
is its generated hash lock. Governance admission belongs to the root project,
not this service. Compile from the repository root with:

```sh
uv pip compile app/inference/requirements.in --python-version 3.13 \
  --python-platform x86_64-unknown-linux-gnu --torch-backend cu128 \
  --generate-hashes --output-file app/inference/requirements.txt
```

The PyTorch-specific resolver option avoids selecting old unrelated packages from
the CUDA index. The Docker install adds that index only with every package version
and distribution hash fixed. The lock targets Linux x86-64 / CPython 3.13; it is
not an ARM/Spark compatibility claim. Do not add `--emit-index-url`: a generated
index option inside the requirements file can reset pip's command-line extra
index and hide the CUDA wheels. The root CPU environment remains separate.

`Dockerfile` is an explicit optional connected development build using approved
online package sources. Its index can encounter the R2 host's HTTP 403 in this
environment; successful connected installation is not claimed.
`Dockerfile.offline` is the default Compose and deployment build path: it uses
the same pinned base and locks with a named, preverified `wheelhouse` build context,
`pip --no-index --only-binary=:all: --require-hashes`, and no runtime downloads.
The base image and complete CPython 3.13 Linux x86-64 wheelhouse must already be
present in the target environment before an offline build. On a connected build
host, provision the complete wheelhouse into a persistent local cache:

```sh
uv run --no-project --python 3.13 --with 'packaging==26.3' \
  python app/inference/provision_wheelhouse.py \
  --destination models/inference-wheelhouse --workers 8
```

This build-only command selects Linux x86-64 CPython 3.13 wheels from official
PyPI metadata and exact PyTorch CUDA/Triton wheel URLs. The canonical
`download.pytorch.org` host is used because the public index's R2 host returned
HTTP 403 in this environment; the upstream index hash is still required. Triton
is also resolved from the PyTorch index because that is the hash-locked source.
Every byte stream must match a
digest already present in `requirements.txt`. Concurrent downloads retain verified
files and resume incomplete files; the final `wheelhouse-manifest.json` records
source URLs, digests and the requirements hash. It does not fetch model files.
Transfer the wheelhouse and pinned base image through the target environment's
approved artifact process before building there. From the repository root:

```sh
docker build --network=none --build-context wheelhouse=/absolute/verified-wheelhouse \
  -f app/inference/Dockerfile.offline -t voiceup-inference:pilot .
docker tag voiceup-inference:pilot voiceup-inference:latest
```

The named context is mounted only during installation and is not copied into the
runtime image. `voiceup-inference:latest` is the local Compose build tag; production
image promotion and digest admission remain the root project's responsibility.
The bank artifact environment has not been provided or tested; a local offline
build is not reported as validation of that deployment environment.

The runtime receives a read-only model volume at `/models/speaker`:

```text
manifest.json
ecapa/hyperparams.yaml
ecapa/embedding_model.ckpt
ecapa/classifier.ckpt
ecapa/mean_var_norm_emb.ckpt
ecapa/label_encoder.txt
silero/silero_vad.jit
```

`model_bundle.py` fixes the repository, immutable revision, complete file allowlist
and SHA-256 digests. A manifest cannot change the trusted hashes. The five ECAPA
files are from [revision 0f99f2d0ebe89ac095bcc5903c4dd8f72b367286](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/tree/0f99f2d0ebe89ac095bcc5903c4dd8f72b367286).
The model card declares Apache-2.0. Silero's JIT comes from the
[silero-vad 6.2.1 package](https://pypi.org/project/silero-vad/6.2.1/).
No model, package, custom Python module or remote URL is downloaded at runtime.

Package previously provisioned files without network access:

```sh
python scripts/package-speaker-model.py \
  --ecapa-source models/ecapa/0f99f2d0ebe89ac095bcc5903c4dd8f72b367286 \
  --silero-jit /path/to/silero_vad/data/silero_vad.jit \
  --output models/speaker-pilot
python scripts/package-speaker-model.py --output models/speaker-pilot --verify
```

The command refuses to overwrite existing output and validates all inputs before
creating the package. It accepts SpeechBrain's cached `label_encoder.ckpt` alias
only when its content matches the upstream `label_encoder.txt` hash. An interrupted
copy remains unready and is never treated as a complete package.

## Processing

The service extends the reference `SpeechBrainEmbedder` and `SileroVAD` loaders
with local verified paths and `FetchConfig(allow_network=False)`. It reuses
`voiceup.audio.Audio`, turn validation and `voiceup.pipeline.extract_evidence`.
The image copies that existing Python package without installing its CPU extras.

One process loads one ECAPA instance and one local Silero JIT instance. Startup
requires the configured CUDA device, expected PyTorch/CUDA build, a CUDA allocation
and kernel, model hash verification, and a warmup of both models. Missing hardware
or model files produce explicit readiness errors. There is no CPU fallback.
The silence warmup establishes operational readiness, not recognition accuracy.

The admission lock covers upload, decode and inference. A concurrent request is
rejected with `503 inference_busy`; the PostgreSQL worker owns the durable queue.
`GET /live` confirms that the HTTP process is alive; `GET /ready` succeeds only
after model initialization. The service holds no profile state and cannot create
or modify a speaker profile. Do not run multiple Uvicorn worker processes.

WAV/FLAC headers and actual libsndfile formats are checked. Requests are capped at
50 MiB; duration at 120 seconds; decoded allocation at 24 million float samples.
Unsupported sample rates/channels are rejected before allocation. Stereo/multichannel
audio is downmixed and resampled to 16 kHz. Heavy clipping is rejected before
channel averaging. VAD does not prove that only one speaker is present.

The reference quality checks keep independent 3–8 second windows, reject low-energy
or clipped windows, and require pairwise consistency of at least 0.55. Enrollment
requires at least 10 usable seconds and two windows; identification requires three
usable seconds and one window. These are development thresholds, not calibrated
probabilities or a measured Turkish-recognition guarantee.

## Configuration and transport

`voiceup_inference.config.Settings` is the sole environment loader.
[.env.example](.env.example) lists every `VOICEUP_INFERENCE_` setting. The internal
key is required, with at least 32 bytes. It is supplied by the root Compose or
existing Kubernetes Secret boundary and never written into a model or image.

`POST /v1/embeddings?purpose=enroll|identify` accepts raw WAV/FLAC bytes, plus
`X-Inference-Key`, `X-Job-Id` and `X-Tenant-Id`. Both context IDs must be UUIDs.
The response fields are `embedding`, `speech_seconds`, `windows_count`, `model_id`,
`model_revision`, `dimensions`, `device`, and optional quality diagnostics.
`speech_seconds` counts accepted usable windows. Raw vectors stay on this private
boundary. Errors use `{"detail":{"code":"stable_code","message":"safe explanation"}}`.
With real CUDA handles, quality diagnostics include per-request PyTorch peak
allocated/reserved bytes, measured after synchronization and a peak reset; those
numbers include resident models and are not whole-device VRAM usage. Unit doubles
omit GPU memory fields. Execution time includes decoding and model processing;
upload and the worker's queue delay are measured separately.
The authoritative contract is maintained with the Accepted PRD's `contracts.md`.
Structured request logs contain only the canonical job UUID, known route label,
HTTP status, elapsed time and configured device. Unknown URL paths, tenant IDs,
request bodies, speaker vectors and authentication headers are not logged.

## Verification

Run `pytest app/inference/tests` with the isolated CPython 3.13 test environment
and the non-ML runtime dependencies installed. Tests use actual WAV/FLAC decoding
and explicit deterministic model doubles. They do not load synthetic models as a
GPU readiness shortcut. Package checks use the filesystem and compiled digest
allowlist. Run the model packaging verifier separately against the real package.

The final image must be tested with runtime networking disabled and a real GPU:
successful `/ready`, a real WAV/FLAC `identify` request, explicit invalid-audio and
quality rejections, and CUDA device evidence. Recognition quality requires the
user's separate-session speaker dataset; neither unit tests nor warmup substitute
for that experiment.

`smoke_cuda.py` is a build-host verification script, not part of the runtime
package. Run it by a read-only bind mount into the finished image with `--gpus all`,
`--network=none`, a read-only model package and one or more prepared 30-second
public speech fixtures. It starts real localhost HTTP, checks readiness and
rejections, sends WAV and FLAC requests, and emits timing, dimension/norm and GPU
allocator metadata without vectors or authentication keys. Repeated public clips
are explicitly labelled constructed software fixtures; these results cannot
establish speaker-identification accuracy.
