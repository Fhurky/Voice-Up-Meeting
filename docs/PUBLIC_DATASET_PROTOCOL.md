# Public speaker-identity evaluation protocol

The `kt-vibecoding-python-web-v2` application is evaluated through its existing
HTTP upload, enrollment and identification contracts. The selected corpus is
LibriSpeech, obtained directly from OpenSLR; dataset preparation neither trains a
model nor changes the on-premise inference boundary. Preparation is an explicit
network operation, while inference remains on the prepared Spark device.

## Source and attribution

LibriSpeech contains segmented, 16 kHz English audiobook speech and is published
under CC BY 4.0. Attribution: **Vassil Panayotov, Guoguo Chen, Daniel Povey and
Sanjeev Khudanpur, “LibriSpeech: an ASR corpus based on public domain audio books,”
ICASSP 2015**. Audio derives from the LibriVox project. Retain the downloaded
`LICENSE.TXT`, `README.TXT` and archive provenance with derived clips.
[Official corpus](https://www.openslr.org/12),
[paper](https://www.danielpovey.com/files/2015_icassp_librispeech.pdf),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

| Split | Purpose | Speakers | Compressed bytes | Official download |
| --- | --- | ---: | ---: | --- |
| dev-clean | Calibration | 40 | 337,926,286 | [Archive](https://www.openslr.org/resources/12/dev-clean.tar.gz) |
| dev-other | Calibration | 33 | 314,305,928 | [Archive](https://www.openslr.org/resources/12/dev-other.tar.gz) |
| test-clean | Held-out evaluation | 40 | 346,663,984 | [Archive](https://www.openslr.org/resources/12/test-clean.tar.gz) |
| test-other | Held-out evaluation | 33 | 328,757,843 | [Archive](https://www.openslr.org/resources/12/test-other.tar.gz) |

The four archives total **1,327,654,041 bytes** before extraction and derived WAV
files. The official [MD5 manifest](https://www.openslr.org/resources/12/md5sum.txt)
is pinned in the preparation script; each downloaded archive also receives a
local SHA-256 digest. HTTPS transfer, an exact byte limit, timeouts, path checks
and rejection of links/device entries complement these integrity checks.

## Deterministic selection

Selection uses the fixed seed `voiceup-librispeech-open-set-v1` and corpus reader,
chapter and utterance identifiers. No inference score, person name, demographic
attribute or listening-based quality ranking determines the selected speakers.
The published source labels provide ground truth; real-world identification of
the audiobook readers is unnecessary.

Each phase selects **50 speakers to enroll and 20 initially unknown speakers**.
The calibration pool uses only development splits; the final pool uses only test
splits. The script verifies that their selected speaker IDs are disjoint.
Gallery order is fixed for nested 5, 10, 20 and 50-person experiments.

For each known speaker, the enrollment clip contains at least 30 seconds and
three query clips each contain at least 15 seconds. Every query comes from a
different original chapter than that speaker's enrollment. One chapter may
supply multiple queries. Each unknown speaker supplies five query clips. One
initially unknown speaker is reserved for subsequent enrollment and return:
initial queries, new enrollment and return query use three distinct chapters.
This yields **302 prepared recordings per phase: 140 distinct selected speakers
and 604 clips across the two phases**. The source pools contain 146 speakers;
six are not selected. These are dataset counts, not successful enrollment or
recognition counts. Preparation fails if the
required counts or source separation cannot be satisfied.

A clip concatenates complete, disjoint utterances from one chapter until its
minimum duration is reached. It retains 16 kHz mono PCM samples and adds no
silence, repeated audio, denoising or resampling. Consequently durations exceed
the requested minimum by up to the last utterance. Source utterance IDs are
never reused across prepared clips. Joining utterances introduces artificial
transitions; these are documented transformations, not original meeting audio.

## Fresh holdout after quality development

Once the first test results have informed a change, all four original source
splits are historical development or regression material. The explicit
`fresh-holdout-v2` protocol selects a separate pool from
[OpenSLR train-clean-100](https://www.openslr.org/resources/12/train-clean-100.tar.gz).
Its compressed size is **6,387,309,499 bytes**, verified by the official HTTPS
response, and its pinned upstream MD5 is
`2a93770f6d5c6c964bc36631d331a522` in the
[official checksum file](https://www.openslr.org/resources/12/md5sum.txt).
This is the 100-hour clean subset of the same
[CC BY 4.0 corpus](https://www.openslr.org/12); the attribution and retained
license requirements above apply. Its `train` label is the corpus publisher's
ASR partition, not evidence that the selected speaker model trained on it.
The model's declared source corpus differs, while person-level training overlap
remains unverified.

The new seed is `voiceup-librispeech-open-set-v2`. Selection excludes every
reader present in the actual audio inventory of the original four raw splits:
40, 33, 40 and 33 disjoint readers, **146 in total**, including the six readers
not selected for the first manifests. Missing or incomplete exclusion inventories
fail before downloading. The corpus-wide `SPEAKERS.TXT` is not an exclusion list:
it also describes readers outside the original four splits. No inference score
or quality rejection affects selection or replaces a selected example.

The fresh pool retains 50 known readers, 20 initially unknown readers, all
302 recording roles and the chapter/utterance separation rules above. The
manifest records `split: test`, `dataset_id: librispeech-open-set-v2-test`, the
new protocol seed, the sorted pseudonymous exclusion IDs and their canonical
JSON SHA-256 digest. `source_split: train-clean-100` identifies the upstream
partition. Neither preparing clips nor inspecting their duration constitutes a
model evaluation. Freeze the candidate before the first inference on this pool;
after any result-dependent change, this pool also becomes regression evidence.

```powershell
./app/backend/.venv/Scripts/python.exe scripts/prepare-public-speaker-dataset.py `
  --protocol fresh-holdout-v2 `
  --exclude-root data/public-speaker-evaluation `
  --download
```

Outputs go to the separate ignored `data/public-speaker-holdout-v2` directory:
`archives/`, `raw/`, `clips/test/` and `test.json`. The previous root is read
without copying its archives. The two roots must not overlap. The original
default command continues to prepare only the original four archives with the
original seed and manifest shape. Existing matching files are reused; conflicts
and partial downloads are preserved and reported as failures.

The fresh archive retains exact transfer size/hash verification, redirect
rejection, a 30-second network timeout and a 1,800-second transfer deadline.
Extraction allows at most 12 GiB and 60,000 members for this pinned source;
the original sources retain their 2 GiB and 20,000-member limits. The 20 MiB
per-member limit and all unsafe-path, link and device-entry checks remain active.
Limit failures require investigation; the preparer does not expand its limits.

Use the fresh manifest and audio root with a fresh, initially empty evaluation
tenant and new state/result paths. Keep the same public application evaluator,
explicit frozen policy and planned denominators. Preserve the first-run evidence
under its original paths; compare it as historical evidence, not as a second
independent blind result.
The new pool contains only the upstream clean partition, whereas the first
experiments combined clean and other partitions. Its aggregate accuracy cannot
alone measure the code change's improvement. Use the original recordings for a
paired historical regression comparison and report fresh-pool accuracy separately.

## Preparation, application evaluation and reporting

Start the prepared application with `Start-VoiceUp.cmd` or
`scripts/connect-spark.ps1`. The following commands run from the repository root
in its prepared Python environment. Prepare the pinned source files first:

```powershell
./app/backend/.venv/Scripts/python.exe scripts/prepare-public-speaker-dataset.py --download
```

Output stays under the ignored `data/public-speaker-evaluation` directory:
`archives/`, `raw/`, `clips/`, `calibration.json` and `test.json`. Manifests contain
gallery order, role, pseudonymous speaker ID, source split, chapter and utterance
IDs, WAV SHA-256, duration, archive provenance and protocol limitations. Existing
matching output is reused; conflicting files or incomplete downloads are
preserved and reported as failures.

The application evaluator is `scripts/evaluate-public-speakers.py`. It requires
pre-created evaluation accounts in separate, initially empty tenants for each
new run. Its private credentials JSON contains `url`, `username`, `password` and
`tenant_id`; the URL must be a loopback HTTP origin. It does not create accounts.
Keep those files under `outputs/public-speaker-evaluation/`, with audio and
manifests under `data/public-speaker-evaluation/`; both directories are ignored.
The ordinary user's profiles and the other evaluation tenants must remain
separate.

The selected candidate policy is
[`selected-policy.json`](evidence/2026-09-09-public-speaker-evaluation/selected-policy.json):
match threshold `0.55`, unknown threshold `0.45`, candidate margin `0.10`.
**Pass `--policy` explicitly for every candidate run.** The option binds the run
to these expected values; it does not change application configuration. Backend
and worker responses must already report that policy, otherwise evaluation
stops. Omitting the argument retains the evaluator's historical `0.75` match
threshold for reproducing the initial baseline.

Run the selected policy on calibration with a fresh evaluation tenant and fresh
state/output paths:

```powershell
./app/backend/.venv/Scripts/python.exe scripts/evaluate-public-speakers.py `
  --manifest data/public-speaker-evaluation/calibration.json `
  --audio-root data/public-speaker-evaluation `
  --credentials outputs/public-speaker-evaluation/calibration-selected-credentials.json `
  --state outputs/public-speaker-evaluation/calibration-selected-state.json `
  --output outputs/public-speaker-evaluation/calibration-selected-results.json `
  --gallery-sizes 50 `
  --policy docs/evidence/2026-09-09-public-speaker-evaluation/selected-policy.json
```

Freeze model revision, policy, preprocessing and quality rules before running
the held-out pool. Use its separate evaluation account:

```powershell
./app/backend/.venv/Scripts/python.exe scripts/evaluate-public-speakers.py `
  --manifest data/public-speaker-evaluation/test.json `
  --audio-root data/public-speaker-evaluation `
  --credentials outputs/public-speaker-evaluation/test-credentials.json `
  --state outputs/public-speaker-evaluation/test-state.json `
  --output outputs/public-speaker-evaluation/test-results.json `
  --gallery-sizes 5,10,20,50 `
  --policy docs/evidence/2026-09-09-public-speaker-evaluation/selected-policy.json
```

Repeat exactly the same command to resume an interrupted run. State binds the
manifest, tenant, origin, gallery sizes, model revision and policy, and holds
idempotency keys and accepted job IDs. A conflicting binding, unexpected profile
change or output without its matching state is rejected. Do not reuse another
run's state or erase state to force retries. The default batch size is four
queued identification jobs; the inference service still computes one at a time.
The runner uploads real files, creates real profiles and checks that
identification leaves the gallery unchanged.

Fifty enrolled speakers is the primary quality target, not an application quota.
The evaluator and metric parser support manifests with up to 200 known and 200
unknown speakers within the existing 1,500-recording and 20,000-operation resource
bounds; selected gallery sizes must fit the manifest. These are evaluation input
budgets, not product limits. A 200-person gallery can still enroll its reserved
newcomer as the 201st profile. This support does not mean such a dataset was
prepared or a 200-person model experiment passed. Old reports remain unchanged.

All final decisions come from the public application API. A Spark-only
diagnostic that calls the same model and computes a candidate threshold table
helps choose the policy on calibration; it does not establish application
behavior. Once held-out results influence a change, a rerun of those same
recordings is regression evidence, not a new blind experiment.

Include all scheduled queries in the denominator. Report correct identity,
wrong identity, unknown, ambiguous, quality rejection and execution failure
separately, with counts at each gallery size. After initial unknown trials,
explicitly enroll the reserved newcomer and test the separate return clip.
Record model revision, device, settings, profile IDs and server job IDs. Scores
from application decisions must not be replaced by an unrelated offline matcher.
Planned gallery size and successfully enrolled gallery size are reported
separately; a rejected enrollment does not remove that person's planned queries.
A terminal job or a runner exit code of zero does not mean that recognition
quality passed.

The current application accepts newcomer enrollment at 50 or 200 profiles under
the ordinary quality and authorization rules. For compatibility with historical
capacity-limited deployments, the runner still recognizes exact HTTP 409
`profile_limit` on new enrollment as a persisted terminal failed operation without
inventing a server job, result or timing; resume does not submit it again. The
return query and final gallery check continue, and the failed newcomer experiment
remains separate from completed main scores. Other HTTP 409 errors remain fatal.
Historical capacity failure is not speech-quality failure or successful unknown
detection, and no profile is silently deleted to bypass it.
The historical `job_status_counts` field counts recorded evaluation operations;
a failed operation rejected before job creation does not imply a server job.

Keep raw results, detailed diagnostic scores, job/profile/tenant IDs and resume
state private under the ignored `outputs/` directory. Produce a shareable
aggregate with `scripts/report-public-speakers.py`:

```powershell
./app/backend/.venv/Scripts/python.exe scripts/report-public-speakers.py `
  --input outputs/public-speaker-evaluation/test-results.json `
  --output docs/evidence/2026-09-09-public-speaker-evaluation/test-summary.json
```

Use the analogous calibration paths for its summary. The reporter refuses to
overwrite an existing output. It removes person, account and job identities,
retains planned denominators and quality errors, and reports source-split counts,
timings and descriptive speaker-cluster bootstrap intervals. Unknown failures
are not successful rejections: read observed false accepts together with the
worst-case bound. Nested galleries reuse probes and are not independent
replications. Publishing a summary requires reviewing its content; raw audio,
credentials and raw operation reports remain outside version control.

The reported execution latency is server job wall time from its first start to
terminal completion, not isolated GPU computation time. Timing aggregates include
terminal identification jobs with quality failures and retries when present;
queue latency is reported separately. Each timing field includes its observed
sample count, and p50/p95 use the nearest-rank convention.

## Hash identities

The following SHA-256 values identify different objects and must not be
compared as if they were interchangeable:

| Location | Hashed content |
| --- | --- |
| Preparation stdout `manifest_sha256` | Exact bytes of the prepared manifest file, including whitespace |
| Evaluator `binding.manifest_sha256` | Parsed manifest serialized as UTF-8 JSON with sorted keys, compact separators and `ensure_ascii=False` |
| Aggregate report `manifest_sha256` | The evaluator's canonical manifest digest, copied unchanged |
| Aggregate `private_source_report_sha256` | Exact bytes of the private application result file |
| Recording `sha256` | Exact bytes of that prepared WAV file |
| Archive provenance `sha256` | Exact downloaded archive bytes, alongside the separately pinned upstream MD5 |

Canonical and raw manifest digests can differ solely because of JSON formatting.
Source and clip provenance still travels with the parsed manifest; canonical
serialization does not discard its fields. The evidence report should label
which digest it records.

## What this can establish

This is an English, read-speech, chapter-separated benchmark for persistent
identity and open-set application behavior. It can expose matching, bookkeeping,
threshold, quality-filter and scale failures. It cannot establish Turkish
meeting accuracy, distinct-day or microphone robustness, overlapping-speaker
separation, transcription accuracy, long-recording support or production safety.
Chapter IDs describe source recordings; they do not prove independently captured
sessions. Queries from the same speaker/chapter remain correlated.

The current [SpeechBrain model card](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb)
declares VoxCeleb 1 and 2 training. LibriSpeech is a different source corpus;
person-level overlap with the training identities has not been audited. Do not
label the test definitively training-identity-free. The model card's VoxCeleb
score is not this application's open-set accuracy.

Twenty unknown speakers with five queries each supply only 100 unknown trials.
Even zero false accepts does not demonstrate a true error rate below 1%; report
the small sample and speaker/chapter dependence rather than a perfection claim.

## Additional datasets considered

The [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/) publishes about
100 hours of English meetings, synchronized close/far microphones and speaker
annotations under CC BY 4.0. Its [download page](https://groups.inf.ed.ac.uk/ami/download/)
provides 22 MB manual annotations and selectable audio; four individual headsets
average approximately 120 MB per meeting. This is a suitable separate meeting
evaluation source once the corresponding multi-speaker capability is accepted
and implemented. This run does not claim AMI or meeting coverage.

The [official Common Voice Turkish 26.0 datasheet](https://mozilladatacollective.com/datasets/cmqinosfq00x4nr07gnk0rdf9)
lists CC0 but also explicitly prohibits attempts to determine speaker identity.
It is therefore excluded from this speaker-identity evaluation. The Turkish
[MediaSpeech corpus](https://www.openslr.org/108) supplies speech/transcript
pairs for speech recognition, but its published description does not establish
the cross-session speaker identity labels required here. Representative Turkish
meeting acceptance still requires an appropriately labeled and authorized source.
