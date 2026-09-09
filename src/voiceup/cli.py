"""Local CLI. Core commands do not import or download neural models."""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

import numpy as np

from .audio import Turn, load_audio, validate_turns
from .identity import MatchPolicy, identify, normalize_embedding
from .pipeline import analyze, extract_evidence
from .registry import Registry


def _write_json(value: object, output: str | None) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    if output is None:
        print(rendered)
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as f:
        f.write(rendered + "\n")
        temporary = Path(f.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Sonuç yazıldı: {path.resolve()}", file=sys.stderr)


def _read_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _policy(args: argparse.Namespace) -> MatchPolicy:
    return MatchPolicy(args.match_threshold, args.new_threshold, args.min_margin)


def _single_speaker_turns(audio) -> list[Turn]:
    from .backends import SileroVAD

    return validate_turns(
        [
            Turn(start, end, "SPEAKER_00")
            for start, end in SileroVAD().speech_spans(audio.samples, audio.sample_rate)
        ],
        audio.duration,
    )


def _demo() -> dict:
    """Synthetic vectors validate memory logic, never claim voice recognition accuracy."""
    rng = np.random.default_rng(42)
    # Orthogonal base vectors make this demo deterministic and well separated.
    bases = np.linalg.qr(rng.normal(size=(192, 6)))[0].T
    meeting1, meeting2 = [], []
    with tempfile.TemporaryDirectory(prefix="voiceup_demo_") as folder:
        db = Path(folder) / "speakers.sqlite3"
        with Registry(db, "synthetic-demo-v1", 192) as registry:
            for vector in bases[:5]:
                p = registry.enroll(vector)
                meeting1.append({"name": p.name, "speaker_id": p.speaker_id})
        with Registry(db, "synthetic-demo-v1", 192) as registry:
            for vector in bases:
                query = normalize_embedding(vector + rng.normal(0, 0.005, 192))
                decision = identify(query, registry.list_speakers())
                if decision.status == "unknown":
                    p = registry.enroll(query)
                    meeting2.append({"status": "new", "name": p.name, "speaker_id": p.speaker_id})
                else:
                    names = {p.speaker_id: p.name for p in registry.list_speakers()}
                    meeting2.append(
                        {
                            "status": decision.status,
                            "name": names.get(decision.speaker_id),
                            "speaker_id": decision.speaker_id,
                        }
                    )
            count = len(registry.list_speakers())
        passed = (
            count == 6
            and all(
                meeting1[i]["speaker_id"] == meeting2[i]["speaker_id"]
                and meeting2[i]["status"] == "recognized"
                for i in range(5)
            )
            and meeting2[5]["status"] == "new"
        )
    return {
        "synthetic_demo": True,
        "note": "Bellek akışı testi; gerçek ses doğruluk ölçümü değildir.",
        "meeting_1": meeting1,
        "meeting_2_after_reopen": meeting2,
        "total_profiles": count,
        "passed": passed,
    }


def _doctor() -> dict:
    versions = {}
    for package in [
        "voiceup",
        "numpy",
        "soundfile",
        "torch",
        "torchaudio",
        "speechbrain",
        "silero-vad",
        "pyannote.audio",
        "torchcodec",
    ]:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    result = {
        "python": sys.version.split()[0],
        "packages": versions,
        "hf_token_configured": bool(os.environ.get("HF_TOKEN")),
        "cuda_available": False,
        "note": "HF erişimi ve model doğruluğu bu komutla sınanmaz.",
    }
    if versions["torch"]:
        import torch

        result["cuda_available"] = torch.cuda.is_available()
        result["torch_cuda_version"] = torch.version.cuda
        if torch.cuda.is_available():
            result["gpu"] = torch.cuda.get_device_name(0)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VoiceUp: toplantılar arasında kalıcı ses kimliği")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("demo", "doctor"):
        cmd = commands.add_parser(command)
        cmd.add_argument("--output")
    evaluation = commands.add_parser(
        "evaluate", help="Etiketli kimlik kararlarından FPIR ve DIR hesapla"
    )
    evaluation.add_argument("decisions", help="JSON karar listesi")
    evaluation.add_argument("--output")

    for command in ("enroll", "identify", "analyze", "profiles"):
        cmd = commands.add_parser(command)
        cmd.add_argument("--db", default="data/speakers.sqlite3")
        cmd.add_argument("--output")
        if command == "profiles":
            actions = cmd.add_subparsers(dest="action", required=True)
            actions.add_parser("list")
            rename = actions.add_parser("rename")
            rename.add_argument("speaker_id")
            rename.add_argument("name")
            delete = actions.add_parser("delete")
            delete.add_argument("speaker_id")
            continue
        cmd.add_argument("audio", help="WAV/FLAC ses dosyası; enroll/identify yalnız tek konuşmacı")
        cmd.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
        cmd.add_argument("--channel", type=int, help="Sıfırdan başlayan kanal indeksi")
        cmd.add_argument("--model-cache", default="models/ecapa")
        if command == "enroll":
            group = cmd.add_mutually_exclusive_group()
            group.add_argument("--name")
            group.add_argument("--speaker-id", help="Mevcut kişiye açıkça yeni örnek ekle")
        else:
            cmd.add_argument("--match-threshold", type=float, default=0.75)
            cmd.add_argument("--new-threshold", type=float, default=0.45)
            cmd.add_argument("--min-margin", type=float, default=0.10)
        if command == "analyze":
            cmd.add_argument(
                "--learn-new", action="store_true", help="Yeterli kanıtlı yeni sesi kalıcı kaydet"
            )
            cmd.add_argument(
                "--turns", help="Diarization yerine doğrulanmış start/end/speaker JSON listesi"
            )
            cmd.add_argument("--num-speakers", type=int)
            cmd.add_argument("--min-speakers", type=int)
            cmd.add_argument("--max-speakers", type=int)
    return parser


def run(args: argparse.Namespace) -> dict | list:
    if args.command == "demo":
        return _demo()
    if args.command == "doctor":
        return _doctor()
    if args.command == "evaluate":
        from .evaluation import evaluate_decisions

        return evaluate_decisions(_read_json(args.decisions))
    from .backends import SpeechBrainEmbedder

    embedder = SpeechBrainEmbedder(
        cache_dir=getattr(args, "model_cache", "models/ecapa"),
        device=getattr(args, "device", "cpu"),
    )
    if args.command == "profiles":
        with Registry(args.db, embedder.model_id, embedder.dimension) as registry:
            if args.action == "rename":
                registry.rename(args.speaker_id, args.name)
            elif args.action == "delete":
                registry.delete(args.speaker_id)
            return [
                {"speaker_id": p.speaker_id, "name": p.name, "samples": len(p.embeddings)}
                for p in registry.list_speakers()
            ]
    policy = None if args.command == "enroll" else _policy(args)
    audio = load_audio(args.audio, args.channel)
    if args.command in ("enroll", "identify"):
        turns = _single_speaker_turns(audio)
    elif args.turns:
        if any(x is not None for x in (args.num_speakers, args.min_speakers, args.max_speakers)):
            raise ValueError("--turns ile konuşmacı sayısı seçenekleri birlikte kullanılamaz.")
        payload = _read_json(args.turns)
        if not isinstance(payload, list):
            raise ValueError("Konuşma aralıkları bir JSON listesi olmalı.")
        try:
            turns = validate_turns([Turn(**item) for item in payload], audio.duration)
        except (TypeError, KeyError) as exc:
            raise ValueError("Her aralık start, end, speaker alanlarını içermeli.") from exc
    else:
        from .backends import PyannoteDiarizer

        turns = [
            Turn(*turn)
            for turn in PyannoteDiarizer(device=args.device).diarize(
                audio.samples,
                audio.sample_rate,
                num_speakers=args.num_speakers,
                min_speakers=args.min_speakers,
                max_speakers=args.max_speakers,
            )
        ]
    with Registry(args.db, embedder.model_id, embedder.dimension) as registry:
        if args.command == "enroll":
            evidence = extract_evidence(audio, turns, "SPEAKER_00", embedder)
            if evidence.embedding is None or evidence.used_seconds < 10 or evidence.windows < 2:
                raise ValueError(
                    "Kayıt için en az 10 saniye kullanılabilir tek konuşmacı sesi ve "
                    f"iki tutarlı pencere gerekli: {evidence.reason}, "
                    f"{evidence.used_seconds:.1f} saniye. 20–30 saniyelik örnek deneyin."
                )
            profile = registry.enroll(
                evidence.embedding, name=args.name, speaker_id=args.speaker_id
            )
            return {
                "speaker_id": profile.speaker_id,
                "name": profile.name,
                "samples": len(profile.embeddings),
                "used_seconds": evidence.used_seconds,
                "model_id": embedder.model_id,
            }
        result = analyze(
            audio,
            turns,
            embedder,
            registry,
            policy=policy,
            learn_new=getattr(args, "learn_new", False),
        )
    result["segmentation_source"] = (
        "silero_vad_single_speaker"
        if args.command == "identify"
        else "provided_turns"
        if args.turns
        else "pyannote_community_1"
    )
    if result["segmentation_source"] == "pyannote_community_1":
        result["segmentation_revision"] = PyannoteDiarizer.revision
    return result


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
        _write_json(result, args.output)
    except (ValueError, RuntimeError, OSError, KeyError, sqlite3.Error) as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 2
    return 0
