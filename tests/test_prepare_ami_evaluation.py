"""AMI benchmark preparation verifies pinned references and audio without network access."""

import hashlib
import importlib.util
import io
import json
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ami():
    spec = importlib.util.spec_from_file_location(
        "prepare_ami_evaluation", ROOT / "scripts/prepare-ami-evaluation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wav_bytes(*, rate=16000, channels=1, seconds=0.5) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"\x01\x00" * int(rate * seconds) * channels)
    return buffer.getvalue()


def ami_style_wav(seconds=0.5) -> bytes:
    """Broadcast-wave layout seen in AMI: metadata chunks, an odd chunk and one stray byte."""
    plain = wav_bytes(seconds=seconds)
    body = plain[12:] + b"LIST" + (4).to_bytes(4, "little") + b"INFO"
    body += b"bext" + (5).to_bytes(4, "little") + b"abcde" + b"\x00" + b"\x07"
    return b"RIFF" + (len(body) + 4).to_bytes(4, "little") + b"WAVE" + body


def accounts_for_every_byte(payload: bytes) -> bool:
    """The server's completed-upload rule: RIFF chunks consume the whole file exactly."""
    if int.from_bytes(payload[4:8], "little") + 8 != len(payload):
        return False
    offset = 12
    while offset < len(payload):
        if len(payload) - offset < 8:
            return False
        size = int.from_bytes(payload[offset + 4 : offset + 8], "little")
        offset += 8 + size + size % 2
    return offset == len(payload)


RTTM = b"SPEAKER ES2004a 1 0.37 1.39 <NA> <NA> MEO015 <NA> <NA>\nSPEAKER ES2004a 1 10.99 3.54 <NA> <NA> FEE013 <NA> <NA>\n"
UEM = b"ES2004a 1 0.000 1049.354687\n"


def fixture_manifest(ami, audio: bytes) -> dict:
    def reference(kind, payload):
        folder = "only_words/rttms" if kind == "rttm" else "uems"
        return {
            "path": f"{folder}/test/ES2004a.{kind}",
            "size_bytes": len(payload),
            "git_blob_sha1": ami.git_blob_sha1(payload),
        }

    return {
        "meetings": [
            {
                "meeting": "ES2004a",
                "split": "test",
                "references": {"rttm": reference("rttm", RTTM), "uem": reference("uem", UEM)},
                "audio": {
                    condition: {"file": f"ES2004a.{suffix}.wav", "size_bytes": len(audio)}
                    for condition, suffix in ami.CONDITIONS.items()
                },
            }
        ]
    }


class FixtureResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FixtureOpener:
    def __init__(self):
        self.urls = []

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        return FixtureResponse(RTTM if request.full_url.endswith(".rttm") else UEM)


def test_committed_manifest_pins_dev_and_test_meetings(ami):
    manifest = ami.load_manifest()
    assert len(manifest["meetings"]) == 34
    assert {row["split"] for row in manifest["meetings"]} == {"dev", "test"}
    assert all(set(row["audio"]) == {"headset", "array1"} for row in manifest["meetings"])


@pytest.mark.parametrize(
    "change",
    [
        lambda m: m.update(setup_revision="0" * 40),
        lambda m: m["meetings"][0]["references"]["rttm"].update(path="only_words/rttms/dev/other.rttm"),
        lambda m: m["meetings"][0]["audio"]["headset"].update(file="../escape.wav"),
        lambda m: m["meetings"].append(dict(m["meetings"][0])),
    ],
)
def test_manifest_rejects_changed_source_identity(ami, tmp_path, change):
    manifest = json.loads(ami.MANIFEST.read_text(encoding="utf-8"))
    change(manifest)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_ami_manifest"):
        ami.load_manifest(path)


def test_references_match_git_blob_identity(ami):
    reference = {"size_bytes": len(RTTM), "git_blob_sha1": ami.git_blob_sha1(RTTM)}
    ami.verify_reference(reference, RTTM)
    with pytest.raises(ValueError, match="reference_hash_mismatch"):
        ami.verify_reference(reference, RTTM.replace(b"FEE013", b"FEE014"))


@pytest.mark.parametrize(
    "url",
    [
        "http://groups.inf.ed.ac.uk/ami/file.wav",
        "https://example.com/ami/file.wav",
        "https://user@groups.inf.ed.ac.uk/ami/file.wav",
    ],
)
def test_untrusted_audio_urls_are_rejected(ami, url):
    with pytest.raises(ValueError, match="untrusted_download_url"):
        ami.validate_url(url, ami.AUDIO_HOSTS)


def test_wav_header_accepts_only_16khz_mono_pcm16(ami, tmp_path):
    good = tmp_path / "good.wav"
    good.write_bytes(wav_bytes())
    assert ami.wav_info(good) == {"sample_rate": 16000, "duration_seconds": 0.5}
    for name, payload in (("stereo", wav_bytes(channels=2)), ("rate", wav_bytes(rate=8000))):
        path = tmp_path / f"{name}.wav"
        path.write_bytes(payload)
        with pytest.raises(ValueError, match="unsupported_audio_format"):
            ami.wav_info(path)


def test_rttm_and_uem_parsing_rejects_foreign_or_malformed_rows(ami):
    assert ami.rttm_speakers(RTTM, "ES2004a") == ["FEE013", "MEO015"]
    assert ami.uem_bounds(UEM, "ES2004a") == (0.0, 1049.354687)
    with pytest.raises(ValueError, match="invalid_rttm"):
        ami.rttm_speakers(RTTM, "ES2004b")
    with pytest.raises(ValueError, match="invalid_uem"):
        ami.uem_bounds(b"ES2004a 1 5 2\n", "ES2004a")


def test_prepare_writes_verified_protocol_and_reuses_files(ami, tmp_path):
    audio = wav_bytes()
    downloads = []

    def downloader(url, temporary):
        downloads.append(url)
        temporary.write_bytes(audio)

    opener = FixtureOpener()
    manifest = fixture_manifest(ami, audio)
    protocol = ami.prepare(tmp_path, manifest=manifest, opener=opener, downloader=downloader)
    row = protocol["meetings"][0]
    assert row["speakers"] == ["FEE013", "MEO015"]
    assert row["audio"]["headset"]["sha256"] == hashlib.sha256(audio).hexdigest()
    assert len(downloads) == 2 and len(opener.urls) == 2
    assert all(ami.SETUP_REVISION in url for url in opener.urls)
    ami.prepare(tmp_path, manifest=manifest, opener=opener, downloader=downloader)
    assert len(downloads) == 2 and len(opener.urls) == 2
    assert not list(tmp_path.rglob("*.partial"))


def test_upload_copy_is_canonical_pcm_with_identical_samples_and_verified_source(ami, tmp_path):
    source = ami_style_wav()
    assert not accounts_for_every_byte(source)
    manifest = fixture_manifest(ami, source)
    protocol = ami.prepare(
        tmp_path,
        manifest=manifest,
        opener=FixtureOpener(),
        downloader=lambda url, temporary: temporary.write_bytes(source),
    )
    entry = protocol["meetings"][0]["audio"]["array1"]
    upload = (tmp_path / entry["path"]).read_bytes()
    assert accounts_for_every_byte(upload) and len(upload) == 44 + len(wav_bytes()) - 44
    assert upload[44:] == wav_bytes()[44:]
    assert entry["sha256"] == hashlib.sha256(upload).hexdigest() and entry["size_bytes"] == len(upload)
    assert entry["source_sha256"] == hashlib.sha256(source).hexdigest()
    assert entry["source_size_bytes"] == len(source)
    assert (tmp_path / "raw/array1/ES2004a.Array1-01.wav").read_bytes() == source
    assert entry["duration_seconds"] == 0.5 and protocol["schema_version"] == 2


def test_offline_verify_detects_a_changed_raw_source(ami, tmp_path, monkeypatch):
    source = ami_style_wav()
    manifest = fixture_manifest(ami, source)
    ami.prepare(
        tmp_path, manifest=manifest, opener=FixtureOpener(),
        downloader=lambda url, temporary: temporary.write_bytes(source),
    )
    monkeypatch.setattr(ami, "load_manifest", lambda: manifest)
    raw = tmp_path / "raw/headset/ES2004a.Mix-Headset.wav"
    raw.write_bytes(source[:-1] + b"\x08")
    with pytest.raises(ValueError, match="audio_hash_mismatch"):
        ami.verify(tmp_path)


def test_size_mismatch_never_publishes_audio(ami, tmp_path):
    audio = wav_bytes()

    def truncated(url, temporary):
        temporary.write_bytes(audio[:-2])

    with pytest.raises(ValueError, match="audio_size_mismatch"):
        ami.prepare(
            tmp_path,
            manifest=fixture_manifest(ami, audio),
            opener=FixtureOpener(),
            downloader=truncated,
        )
    assert not (tmp_path / "audio/headset/ES2004a.Mix-Headset.wav").exists()
    assert not (tmp_path / "raw/headset/ES2004a.Mix-Headset.wav").exists()
    assert not list(tmp_path.rglob("*.partial"))


def test_offline_verify_detects_changed_audio(ami, tmp_path, monkeypatch):
    audio = wav_bytes()
    manifest = fixture_manifest(ami, audio)
    ami.prepare(
        tmp_path,
        manifest=manifest,
        opener=FixtureOpener(),
        downloader=lambda url, temporary: temporary.write_bytes(audio),
    )
    monkeypatch.setattr(
        ami, "load_manifest", lambda: {**manifest, "meetings": manifest["meetings"]}
    )
    assert ami.verify(tmp_path)["protocol"] == ami.PROTOCOL
    target = tmp_path / "audio/array1/ES2004a.Array1-01.wav"
    target.unlink()
    target.write_bytes(audio[:-2] + b"\x02\x00")
    with pytest.raises(ValueError, match="audio_hash_mismatch"):
        ami.verify(tmp_path)
