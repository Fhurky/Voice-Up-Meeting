from concurrent.futures import ThreadPoolExecutor
import sqlite3

import numpy as np
import pytest

from voiceup.identity import identify
from voiceup.registry import Registry


MODEL = "test/embedding-model@immutable-revision"


def test_five_known_people_then_sixth_persist_across_meetings(tmp_path):
    path = tmp_path / "speakers.sqlite3"
    basis = np.eye(6)
    with Registry(path, MODEL, 6) as registry:
        known = [registry.enroll(vector) for vector in basis[:5]]
        assert [p.name for p in known] == [f"Katılımcı {i}" for i in range(1, 6)]
        assert len({p.speaker_id for p in known}) == 5

    with Registry(path, MODEL, 6) as registry:
        profiles = registry.list_speakers()
        assert [p.speaker_id for p in profiles] == [p.speaker_id for p in known]
        for vector, expected in zip(basis, known):
            decision = identify(vector, profiles)
            assert decision.status == "recognized"
            assert decision.speaker_id == expected.speaker_id
        assert identify(basis[5], profiles).status == "unknown"
        # Unknown recognition never silently enrolls a new identity.
        assert len(registry.list_speakers()) == 5
        sixth = registry.enroll(basis[5])
        assert sixth.name == "Katılımcı 6"

    with Registry(path, MODEL, 6) as registry:
        assert identify(basis[5], registry.list_speakers()).speaker_id == sixth.speaker_id
        assert len(registry.list_speakers()) == 6


def test_explicit_sample_append_is_capped_and_never_renames(tmp_path):
    with Registry(tmp_path / "speakers.db", MODEL, 2) as registry:
        person = registry.enroll([2, 0], name="  Ayşe  ")
        assert person.name == "Ayşe"
        np.testing.assert_array_equal(person.embeddings[0], [1, 0])
        for i in range(25):
            person = registry.enroll([1, i / 100], speaker_id=person.speaker_id)
        assert len(person.embeddings) == Registry.MAX_EXEMPLARS
        assert person.name == "Ayşe"
        assert len(registry.list_speakers()) == 1
        # Oldest retained sample is i=5; newest is i=24.
        assert person.embeddings[0][1] / person.embeddings[0][0] == pytest.approx(0.05)
        assert person.embeddings[-1][1] / person.embeddings[-1][0] == pytest.approx(0.24)
        with pytest.raises(ValueError, match="rename"):
            registry.enroll([1, 0], name="Other", speaker_id=person.speaker_id)
        assert registry.list_speakers()[0].name == "Ayşe"


def test_rename_delete_and_numbering_do_not_change_other_ids(tmp_path):
    path = tmp_path / "speakers.db"
    with Registry(path, MODEL, 2) as registry:
        first = registry.enroll([1, 0])
        second = registry.enroll([0, 1])
        registry.enroll([1, 0.1], speaker_id=first.speaker_id)
        registry.rename(first.speaker_id, "Deniz")
        assert registry.list_speakers()[0].name == "Deniz"
        registry.delete(first.speaker_id)
        assert [p.speaker_id for p in registry.list_speakers()] == [second.speaker_id]
        third = registry.enroll([-1, 0])
        assert third.name == "Katılımcı 3"
        with pytest.raises(KeyError):
            registry.rename(first.speaker_id, "Missing")
        with pytest.raises(KeyError):
            registry.delete(first.speaker_id)
        with pytest.raises(KeyError):
            registry.enroll([1, 0], speaker_id=first.speaker_id)
    with sqlite3.connect(path) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM voiceup_embeddings WHERE speaker_id = ?", (first.speaker_id,)
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize("model,dimension", [("different@v2", 2), (MODEL, 3)])
def test_namespace_mismatch_rejected_without_changing_database(tmp_path, model, dimension):
    path = tmp_path / "speakers.db"
    with Registry(path, MODEL, 2) as registry:
        person = registry.enroll([1, 0])
    before = path.read_bytes()
    with pytest.raises(ValueError, match="mismatch"):
        Registry(path, model, dimension)
    assert path.read_bytes() == before
    with Registry(path, MODEL, 2) as registry:
        assert registry.list_speakers()[0].speaker_id == person.speaker_id


@pytest.mark.parametrize("value", [[0, 0], [np.nan, 1], [np.inf, 0], [1, 0, 0], [[1, 0]]])
def test_invalid_enrollment_does_not_allocate_id_or_write(tmp_path, value):
    with Registry(tmp_path / "speakers.db", MODEL, 2) as registry:
        with pytest.raises(ValueError):
            registry.enroll(value)
        assert registry.list_speakers() == []
        assert registry.enroll([1, 0]).name == "Katılımcı 1"


def test_matching_and_mutating_returned_arrays_do_not_update_registry(tmp_path):
    with Registry(tmp_path / "speakers.db", MODEL, 2) as registry:
        person = registry.enroll([1, 0])
        for _ in range(5):
            assert identify([1, 0.01], registry.list_speakers()).speaker_id == person.speaker_id
        detached = registry.list_speakers()
        detached[0].embeddings[0][:] = [0, 1]
        detached[0].name = "Changed outside registry"
        persisted = registry.list_speakers()[0]
        assert persisted.name == "Katılımcı 1"
        assert len(persisted.embeddings) == 1
        np.testing.assert_array_equal(persisted.embeddings[0], [1, 0])


def test_concurrent_enrollment_allocates_unique_sequential_names(tmp_path):
    path = tmp_path / "speakers.db"
    with Registry(path, MODEL, 2):
        pass

    def enroll_person(_):
        with Registry(path, MODEL, 2) as registry:
            return registry.enroll([1, 0])

    with ThreadPoolExecutor(max_workers=4) as pool:
        people = list(pool.map(enroll_person, range(24)))
    assert len({p.speaker_id for p in people}) == 24
    assert {p.name for p in people} == {f"Katılımcı {i}" for i in range(1, 25)}


def test_failed_sample_insert_rolls_back_identity_and_counter(tmp_path):
    path = tmp_path / "speakers.db"
    with Registry(path, MODEL, 2) as registry:
        with sqlite3.connect(path) as connection:
            connection.execute(
                "CREATE TRIGGER reject_sample BEFORE INSERT ON voiceup_embeddings "
                "BEGIN SELECT RAISE(ABORT, 'test failure'); END"
            )
        with pytest.raises(sqlite3.IntegrityError, match="test failure"):
            registry.enroll([1, 0])
        assert registry.list_speakers() == []
        with sqlite3.connect(path) as connection:
            connection.execute("DROP TRIGGER reject_sample")
        assert registry.enroll([1, 0]).name == "Katılımcı 1"


def test_metadata_rechecked_before_writes(tmp_path):
    path = tmp_path / "speakers.db"
    with Registry(path, MODEL, 2) as registry:
        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE voiceup_metadata SET value = 'other@v2' WHERE key = 'model_id'"
            )
        with pytest.raises(ValueError, match="model_id mismatch"):
            registry.enroll([1, 0])
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM voiceup_speakers").fetchone()[0] == 0


def test_unrelated_database_rejected(tmp_path):
    path = tmp_path / "other.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises(ValueError, match="not a complete"):
        Registry(path, MODEL, 2)


@pytest.mark.parametrize("name", ["", "  ", 7])
def test_invalid_names_rejected(tmp_path, name):
    with Registry(tmp_path / "speakers.db", MODEL, 2) as registry:
        with pytest.raises(ValueError, match="name"):
            registry.enroll([1, 0], name=name)
        person = registry.enroll([1, 0])
        with pytest.raises(ValueError, match="name"):
            registry.rename(person.speaker_id, name)


@pytest.mark.parametrize(
    "model,dimension", [("", 2), ("  ", 2), (MODEL, 0), (MODEL, True), (MODEL, 2.5)]
)
def test_invalid_namespace_rejected(tmp_path, model, dimension):
    with pytest.raises(ValueError):
        Registry(tmp_path / "speakers.db", model, dimension)
