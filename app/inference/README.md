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

`VOICEUP_INFERENCE_RUNTIME_PROFILE` explicitly selects the runtime guard:

| Profile | Host architecture | Required PyTorch | Required CUDA build |
| --- | --- | --- | --- |
| `x86_64-cu128` (default) | x86_64, including AMD64 alias | 2.8.0 | 12.8 |
| `aarch64-cu129` (opt-in) | aarch64, including arm64 alias | 2.8.0 | 12.9 |

Both profiles require a configured CUDA device, a real CUDA allocation, kernel
and synchronization, followed by ECAPA and Silero warmup. An architecture or
runtime mismatch returns `503 cuda_runtime_mismatch`; a missing GPU or CPU
execution returns `503 cuda_unavailable`. There is no automatic profile selection
or CPU fallback. Profile unit tests use doubles and do not establish ARM64/GPU
compatibility. The ARM64 profile supports the Accepted remote Spark capability;
its separate artifact admission and real target verification are required before
deployment. Selecting it does not adapt or replace the existing x86-64 lock.

The Spark build has its own direct authorities (`requirements.spark.in`), full
artifact manifest (`spark-wheelhouse-manifest.json`), generated hash lock
(`requirements.spark.txt`) and `Dockerfile.spark`. The manifest selects exact
publisher URLs: TorchAudio 2.8.0 has different wheel contents on PyPI and the
PyTorch CUDA index despite sharing a filename. The ARM64 dependency graph has
48 artifacts; the existing x86-64 graph remains unchanged. Provision these only
at build time; the final image installs from its local wheelhouse with networking
disabled and runs `pip check`. Real GB10 execution remains a separate acceptance
point in the [remote Spark PRD](../../specs/speaker-identity/PRDs/004-spark-remote-inference/PRD.md).

The verified Spark image and actual GB10 checks are recorded in the
[native report](../../docs/evidence/2026-09-09-spark-runtime/native-run-report.md).
The [runtime guide](../../docs/SPARK_RUNTIME.md) describes the private Compose
service, CDI device, immutable image selection and Windows SSH startup. Native
Torch emits an SM121 upper-bound warning; the recorded tensor and ECAPA checks
passed, without claiming compatibility for every CUDA kernel or speaker accuracy.

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

The pilot preserves sufficient reference evidence and every original consistency
rejection. Only insufficient evidence can try chronological voiced packing:
original blocks shorter than 1.5 seconds, quiet blocks and clipped blocks cannot
contribute. Original block embeddings must all agree pairwise at 0.55 before
packing; every block must also agree with the pooled result, and any original
partial embedding remains an additional anchor. Profile evidence still uses
independent 3–8 second windows. PCM samples are never repeated and silence never
counts as usable speech. This guard is not speaker diarization: continuous mixed
speech can still pass the original path. The calibration selection and untouched
holdout are recorded in [the recovery report](../../docs/evidence/2026-09-09-speech-recovery/README.md).

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
`quality.preprocessing_version` is `vad-windows-v1` or `vad-packed-fallback-v1`.
Only this strict version label crosses into the public job result; unrelated
producer diagnostics and vectors remain private. Old stored jobs expose `null`.
The label has the existing seven-day job retention, not permanent sample provenance.
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
