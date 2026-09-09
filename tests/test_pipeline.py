"""Fake embeddings and synthetic audio verify orchestration, NOT acoustic accuracy."""

import numpy as np
import pytest

from voiceup.audio import Audio, Turn
from voiceup.pipeline import analyze, extract_evidence
from voiceup.registry import Registry


class AmplitudeEmbedder:
    """Test double: decode a vector index from synthetic noise amplitude."""

    model_id = "synthetic-amplitude-test@v1"
    dimension = 6

    def __init__(self):
        self.calls = 0

    def encode(self, samples, sample_rate=16000):
        assert sample_rate == 16000
        self.calls += 1
        rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        index = int(round(rms / 0.03)) - 1
        assert 0 <= index < self.dimension
        return np.eye(self.dimension)[index]


class ConstantEmbedder(AmplitudeEmbedder):
    def __init__(self, vector):
        super().__init__()
        self.vector = np.array(vector, dtype=float)
        self.dimension = len(self.vector)

    def encode(self, samples, sample_rate=16000):
        self.calls += 1
        return self.vector.copy()


def noise(seconds, identity=0, seed=1):
    samples = np.random.default_rng(seed).standard_normal(round(seconds * 16000)).astype(np.float32)
    samples *= (0.03 * (identity + 1)) / np.sqrt(np.mean(samples.astype(np.float64) ** 2))
    return samples


def meeting(identities, seconds=12):
    audio = Audio(
        np.concatenate(
            [noise(seconds, identity, seed=i + 1) for i, identity in enumerate(identities)]
        )
    )
    turns = [
        Turn(i * seconds, (i + 1) * seconds, f"SPEAKER_{i:02d}") for i in range(len(identities))
    ]
    return audio, turns


def test_five_people_then_sixth_survive_new_recording_and_reload(tmp_path):
    embedder = AmplitudeEmbedder()
    path = tmp_path / "speakers.db"
    with Registry(path, embedder.model_id, embedder.dimension) as registry:
        audio, turns = meeting(range(5))
        first = analyze(audio, turns, embedder, registry, learn_new=True)
        assert [p["status"] for p in first["speakers"]] == ["new"] * 5
        ids = [p["speaker_id"] for p in first["speakers"]]
        assert len(set(ids)) == 5

    with Registry(path, embedder.model_id, embedder.dimension) as registry:
        audio, turns = meeting([4, 2, 0, 3, 1, 5])
        second = analyze(audio, turns, embedder, registry, learn_new=True)
        assert [p["speaker_id"] for p in second["speakers"][:5]] == [
            ids[i] for i in [4, 2, 0, 3, 1]
        ]
        assert [p["status"] for p in second["speakers"][:5]] == ["recognized"] * 5
        assert second["speakers"][5]["status"] == "new"
        assert second["speakers"][5]["name"] == "Katılımcı 6"
        assert len(registry.list_speakers()) == 6
        assert all(len(p.embeddings) == 1 for p in registry.list_speakers())
        sixth_id = second["speakers"][5]["speaker_id"]

    with Registry(path, embedder.model_id, embedder.dimension) as registry:
        audio, turns = meeting([5])
        third = analyze(audio, turns, embedder, registry)
        assert third["speakers"][0]["speaker_id"] == sixth_id


def test_unknown_does_not_enroll_without_explicit_learn_new(tmp_path):
    embedder = AmplitudeEmbedder()
    with Registry(tmp_path / "speakers.db", embedder.model_id, embedder.dimension) as registry:
        audio, turns = meeting([0])
        result = analyze(audio, turns, embedder, registry)
        assert result["speakers"][0]["status"] == "unknown"
        assert result["speakers"][0]["speaker_id"] is None
        assert registry.list_speakers() == []


@pytest.mark.parametrize("seconds", [2.0, 4.0, 9.0])
def test_short_speech_never_enrolls(tmp_path, seconds):
    embedder = AmplitudeEmbedder()
    audio, turns = meeting([0], seconds)
    with Registry(tmp_path / "speakers.db", embedder.model_id, embedder.dimension) as registry:
        result = analyze(audio, turns, embedder, registry, learn_new=True)
        assert result["speakers"][0]["speaker_id"] is None
        assert not result["speakers"][0]["profile_created"]
        assert registry.list_speakers() == []


@pytest.mark.parametrize("sample_value", [0.0, 1.0])
def test_silent_or_heavily_clipped_speech_is_unusable(tmp_path, sample_value):
    embedder = AmplitudeEmbedder()
    audio = Audio(np.full(12 * 16000, sample_value, dtype=np.float32))
    with Registry(tmp_path / "speakers.db", embedder.model_id, embedder.dimension) as registry:
        result = analyze(audio, [Turn(0, 12, "A")], embedder, registry, learn_new=True)
        assert result["speakers"][0]["status"] == "ambiguous"
        assert result["speakers"][0]["reason"] == "insufficient_clean_speech"
        assert registry.list_speakers() == []
        assert embedder.calls == 0


def test_no_speech_or_only_overlap_never_enrolls(tmp_path):
    embedder = AmplitudeEmbedder()
    audio = Audio(noise(12))
    with Registry(tmp_path / "speakers.db", embedder.model_id, embedder.dimension) as registry:
        assert analyze(audio, [], embedder, registry, learn_new=True)["speakers"] == []
        result = analyze(
            audio, [Turn(0, 12, "A"), Turn(0, 12, "B")], embedder, registry, learn_new=True
        )
        assert all(s["status"] == "ambiguous" for s in result["speakers"])
        assert all(s["clean_seconds"] == 0 for s in result["speakers"])
        assert embedder.calls == 0
        assert registry.list_speakers() == []


def test_ambiguous_voice_never_enrolls_or_updates_known_profile(tmp_path):
    embedder = ConstantEmbedder([0.6, 0.8])
    with Registry(tmp_path / "speakers.db", embedder.model_id, 2) as registry:
        person = registry.enroll([1, 0])
        audio, turns = meeting([0])
        result = analyze(audio, turns, embedder, registry, learn_new=True)
        assert result["speakers"][0]["status"] == "ambiguous"
        assert result["speakers"][0]["speaker_id"] is None
        profiles = registry.list_speakers()
        assert len(profiles) == 1
        assert profiles[0].speaker_id == person.speaker_id
        assert len(profiles[0].embeddings) == 1
        np.testing.assert_array_equal(profiles[0].embeddings[0], [1, 0])


def test_simultaneous_labels_cannot_claim_same_registered_identity(tmp_path):
    embedder = AmplitudeEmbedder()
    audio = Audio(noise(28))
    turns = [Turn(0, 16, "A"), Turn(12, 28, "B")]
    with Registry(tmp_path / "speakers.db", embedder.model_id, embedder.dimension) as registry:
        registry.enroll(np.eye(embedder.dimension)[0])
        result = analyze(audio, turns, embedder, registry, learn_new=True)
        assert len(result["speakers"]) == 2
        assert all(s["status"] == "ambiguous" for s in result["speakers"])
        assert all(s["reason"] == "overlapping_identity_conflict" for s in result["speakers"])
        assert all(s["speaker_id"] is None for s in result["speakers"])
        assert len(registry.list_speakers()) == 1


def test_new_split_labels_reuse_first_enrollment_without_duplicate_or_self_update(tmp_path):
    embedder = AmplitudeEmbedder()
    audio, turns = meeting([0, 0])
    with Registry(tmp_path / "speakers.db", embedder.model_id, embedder.dimension) as registry:
        result = analyze(audio, turns, embedder, registry, learn_new=True)
        first, second = result["speakers"]
        assert first["status"] == "new"
        assert second["status"] == "recognized"
        assert first["speaker_id"] == second["speaker_id"]
        assert not second["profile_created"]
        assert len(registry.list_speakers()) == 1
        assert len(registry.list_speakers()[0].embeddings) == 1


def test_inconsistent_windows_do_not_form_a_profile(tmp_path):
    embedder = AmplitudeEmbedder()
    audio = Audio(np.concatenate([noise(6, 0), noise(6, 1)]))
    with Registry(tmp_path / "speakers.db", embedder.model_id, embedder.dimension) as registry:
        result = analyze(audio, [Turn(0, 12, "A")], embedder, registry, learn_new=True)
        assert result["speakers"][0]["reason"] == "inconsistent_voice_windows"
        assert result["speakers"][0]["consistency"] == pytest.approx(0)
        assert registry.list_speakers() == []


def test_compute_cap_samples_across_recording():
    embedder = AmplitudeEmbedder()
    audio = Audio(noise(200))
    evidence = extract_evidence(audio, [Turn(0, 200, "A")], "A", embedder)
    assert evidence.windows == 20
    assert evidence.used_seconds == pytest.approx(160)
    assert evidence.clean_seconds == pytest.approx(200)
    assert embedder.calls == 20


@pytest.mark.parametrize(
    "model_id,dimension", [("wrong-model@v1", 6), (AmplitudeEmbedder.model_id, 7)]
)
def test_pipeline_rejects_model_namespace_mismatch_before_encoding_or_writing(
    tmp_path, model_id, dimension
):
    embedder = AmplitudeEmbedder()
    audio, turns = meeting([0])
    with Registry(tmp_path / "speakers.db", model_id, dimension) as registry:
        with pytest.raises(ValueError, match="model|dimension|namespace"):
            analyze(audio, turns, embedder, registry, learn_new=True)
        assert registry.list_speakers() == []
        assert embedder.calls == 0
