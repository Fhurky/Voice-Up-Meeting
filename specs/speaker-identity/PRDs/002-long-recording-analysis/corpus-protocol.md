# Independent meeting identity corpus protocol

Source: [Accepted PRD Decision 20](PRD.md), [plan](plan.md), task T19.
Profile: `kt-vibecoding-python-web-v2`. Status: Frozen before model execution.

The protocol identifier and deterministic seed are both
`voiceup-meeting-identity-independent-v1`. This is a local, offline preparation
protocol. It neither downloads data nor changes application inference.

## Selection and prior use

Use the existing `train-clean-100` raw corpus under
`data/public-speaker-holdout-v2/raw/LibriSpeech`. Exclude every speaker, utterance
identifier and recording digest in these three immutable manifests:

| Manifest | SHA-256 |
|---|---|
| `data/public-speaker-evaluation/calibration.json` | `a170d8fa88a13bd7059cd3e6e82747e3b05b7dfc7a814a451672cb4f98ac5c33` |
| `data/public-speaker-evaluation/test.json` | `0e4deb4d61e36e378a29e270fc4d1c070d3331a9839314f37261c403d1361ad9` |
| `data/public-speaker-holdout-v2/test.json` | `67fa0170afbe4c3a382a91506cd68d3e635fe7c1d562810c5fe9c2b8ad3c9eb7` |

The original calibration was used for threshold and preprocessing selection.
The historical test was evaluated and replayed. The v2 manifest was evaluated
in 302 jobs on 2026-09-09 and included in subsequent comparisons; its name does
not make it an unseen holdout now. A/B/D/C and the 48 coherence cases derive
from six original calibration speakers. Replays and repeated-source endurance
fixtures are regression or durability evidence, not independent observations.

The read-only inventory found 181 remaining readers: 149 have at least two
chapters and 78 have at least three. Select 50 known readers from the latter,
ordered by SHA-256 of `seed|known|speaker_id`; select 20 never-enrolled readers
from the remaining readers with at least two chapters, ordered with `unknown`
in place of `known`. Ties use the identifier. No model, embedding, VAD, quality
score or recognizability participates in selection. A failed selected reader
is never replaced.

Order each reader's chapters by SHA-256 of
`seed|chapter|speaker_id|chapter_id`. Known enrollment, query 1 and query 2 use
three different chapters. The two never-enrolled queries use two different
chapters. Order a chapter's complete utterances by SHA-256 of
`seed|utterance|utterance_id`. Append complete utterances until reaching 35
seconds, with a hard 60-second limit. An utterance that would exceed the limit
is skipped deterministically; failure to reach the target is a recorded
preparation failure, not permission to select another reader or chapter.
There is no cropping, repetition, resampling, synthetic speech or silence
insertion in these individual clips. PCM must be mono, 16 kHz, signed 16-bit.
Audio duration is not voiced duration; the application's speech and memory
quality checks still decide whether the evidence is usable.

## Output and evaluation boundaries

Write a reusable preparer and immutable local `protocol.json`, 190 planned clip
records, WAV files and separate official-reference text files. There are 50
enrollment clips, 100 known query clips and 40 never-enrolled query clips.
Each clip records its planned reader/role/chapter, preparation status, source
utterance IDs, FLAC digests, complete source frame counts, output frame ranges,
WAV and PCM digests, reference digests and word counts. Bind the protocol to
the exclusion manifests, raw inventory, metadata, source archive identity,
selection policy and preparer source digest. The archive identity comes from
the previously verified source manifest; this run separately verifies selected
FLAC content and does not claim to rehash the entire archive.

Existing outputs may be reused only byte-for-byte; conflicting files fail
closed. Reference text is available only to the offline scorer, never to
inference, identity matching or profile admission. Raw audio, reference text
and embeddings stay in ignored local storage; committed evidence contains
counts, digests and limitations.

Evaluate nested galleries of 5, 10, 20 and 50 using the same fixed 140 probe
sources in every stage. The first N selected known readers are in-gallery;
the other selected readers are out-of-gallery in that stage, in addition to
the 20 never-enrolled readers. Report these unknown groups separately. Every
planned failure and abstention stays in the denominator, and enrollment
coverage states actual as well as intended gallery size. A query must not
enroll an out-of-gallery reader and change the stage's gallery. Nested stages
are correlated and are not pooled as independent observations.

An optional deterministic meeting derivation consumes the completed clips,
without selecting new readers or utterances. For each requested nested size,
assemble A from enrollment, B from query 1 and C from query 2. Iterate readers
in gallery order, taking one complete source utterance per reader each round;
insert exactly 0.25 seconds of silence between utterances. Use every selected
clip frame exactly once. Record source/output frame ranges, speaker IDs,
utterance IDs and separately hashed official references. Bind each derivative
to the immutable clip protocol and WAV hashes; conflicting outputs fail closed.
These actual participant-count meetings and the nested-gallery probe experiment
are separate experiments. Preparing either does not claim that it was run.

This corpus supports independent-person, chapter-separated English audiobook
identity and word-reference evaluation. It does not prove Turkish meeting
quality, different microphones or recording days, manually annotated speech
boundaries, or person independence from a pretrained model's training data.
Once its results influence a change it becomes observed regression data for
later changes; no fresh-holdout claim is silently renewed.
