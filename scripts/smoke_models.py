"""Real local ECAPA/VAD and SQLite persistence smoke check, not an accuracy benchmark.

Samples: SpeechBrain's official tests/samples/ASR directory at tag v1.1.1:
https://github.com/speechbrain/speechbrain/tree/v1.1.1/tests/samples/ASR
Git blob hashes were verified against that repository's GitHub contents API.
The sample filenames supply the two speaker labels; these are short test clips.

This deliberately enrolls full-clip embeddings directly into a temporary Registry,
bypassing the production pipeline's 10-second enrollment evidence requirement.
It validates real model execution and persistence, not production enrollment quality,
cross-session meeting accuracy, diarization, or calibrated decision thresholds.
Only --download-samples fetches public sample audio. Inference runs locally; the
ECAPA adapter may download its pinned public model if it is not already cached.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory
from time import perf_counter
from urllib.request import urlopen

import numpy as np

from voiceup.audio import load_audio
from voiceup.backends import SileroVAD, SpeechBrainEmbedder
from voiceup.identity import MatchPolicy, identify
from voiceup.registry import Registry


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BASE = "https://raw.githubusercontent.com/speechbrain/speechbrain/v1.1.1/tests/samples/ASR/"
SAMPLES = {
    "spk1_snt1.wav": "589c636da71be77f7d9ba070b0872637a86ebd07",
    "spk1_snt2.wav": "be860e28917fbdec3192f0fad23d35317e14877b",
    "spk2_snt1.wav": "a9b83a9b7396164abdc7f509ed9dae123a43f92e",
}


def verify_sample(name: str, content: bytes) -> None:
    git_blob = f"blob {len(content)}\0".encode() + content
    if hashlib.sha1(git_blob).hexdigest() != SAMPLES[name]:
        raise ValueError(f"{name} does not match the verified official SpeechBrain sample")


def sample_paths(download: bool) -> dict[str, Path]:
    paths = {name: ROOT / "data" / "smoke" / name for name in SAMPLES}
    for name, path in paths.items():
        if not path.is_file():
            if not download:
                raise FileNotFoundError(
                    f"Missing {path}. Use --download-samples to fetch the public test clips."
                )
            with urlopen(SOURCE_BASE + name, timeout=60) as response:
                content = response.read(2_000_000)
            verify_sample(name, content)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        verify_sample(name, path.read_bytes())
    return paths


def installed_versions() -> dict[str, str | None]:
    result = {"python": platform.python_version()}
    for package in ("numpy", "torch", "torchaudio", "speechbrain", "silero-vad"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = None
    return result


def run(download: bool, device: str) -> dict:
    started = perf_counter()
    paths = sample_paths(download)
    vad = SileroVAD(device=device)
    embedder = SpeechBrainEmbedder(cache_dir=ROOT / "models" / "ecapa", device=device)
    vectors = {}
    details = []
    for name, path in paths.items():
        audio = load_audio(path)
        spans = vad.speech_spans(audio.samples, audio.sample_rate)
        vector = embedder.encode(audio.samples, audio.sample_rate)
        if vector.shape != (192,) or not np.isfinite(vector).all():
            raise RuntimeError(f"Invalid real-model embedding for {name}")
        vectors[name] = vector
        details.append(
            {
                "file": name,
                "source_url": SOURCE_BASE + name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "source_git_blob_verified": True,
                "duration_seconds": audio.duration,
                "sample_rate": audio.sample_rate,
                "vad_spans_seconds": spans,
                "vad_total_speech_seconds": sum(end - start for start, end in spans),
                "embedding_dimension": int(vector.size),
                "embedding_norm": float(np.linalg.norm(vector)),
            }
        )

    first = vectors["spk1_snt1.wav"]
    held_out = vectors["spk1_snt2.wav"]
    other = vectors["spk2_snt1.wav"]
    same_score = float(np.clip(np.dot(first, held_out), -1.0, 1.0))
    different_score = float(np.clip(np.dot(other, held_out), -1.0, 1.0))
    policy = MatchPolicy()
    with TemporaryDirectory(prefix="voiceup-real-model-smoke-") as directory:
        database = Path(directory) / "speakers.sqlite3"
        with Registry(database, embedder.model_id, embedder.dimension) as registry:
            speaker1 = registry.enroll(first, name="SpeechBrain sample speaker 1")
            speaker2 = registry.enroll(other, name="SpeechBrain sample speaker 2")
            before = identify(held_out, registry.list_speakers(), policy)
        with Registry(database, embedder.model_id, embedder.dimension) as reloaded:
            profiles = reloaded.list_speakers()
            after = identify(held_out, profiles, policy)
            persisted_ids = [profile.speaker_id for profile in profiles]
        if before != after or persisted_ids != [speaker1.speaker_id, speaker2.speaker_id]:
            raise RuntimeError("SQLite reload changed speaker identities or the match decision")

    return {
        "synthetic_demo": False,
        "acoustic_benchmark": False,
        "purpose": "real local VAD/ECAPA execution and SQLite persistence smoke check",
        "production_enrollment_quality_gate_bypassed": True,
        "quality_gate_note": (
            "Full short clips are enrolled directly for this smoke check; "
            "the production pipeline requires at least 10 seconds of usable enrollment speech."
        ),
        "model_id": embedder.model_id,
        "device": device,
        "installed_versions": installed_versions(),
        "samples": details,
        "cosine_scores": {
            "same_speaker_spk1_snt1_vs_spk1_snt2": same_score,
            "different_speaker_spk2_snt1_vs_spk1_snt2": different_score,
            "same_speaker_score_is_higher": same_score > different_score,
        },
        "identity": {
            "policy": asdict(policy),
            "thresholds_are_provisional": True,
            "expected_speaker_id": speaker1.speaker_id,
            "other_speaker_id": speaker2.speaker_id,
            "before_reload": asdict(before),
            "after_reload": asdict(after),
            "persisted_profile_count": len(persisted_ids),
            "reload_preserved_decision": before == after,
            "held_out_clip_recognized_correctly": after.speaker_id == speaker1.speaker_id,
            "temporary_registry_removed": True,
        },
        "elapsed_seconds": round(perf_counter() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-samples", action="store_true")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "real-model-smoke.json")
    args = parser.parse_args()
    report = run(args.download_samples, args.device)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
