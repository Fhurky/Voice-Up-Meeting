"""Compare the production correction adapter on frozen Turkish text, without database writes.

The existing backend container supplies the admitted runtime. The host controller
keeps private references/results under outputs and publishes aggregates only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from experiment_ledger import (
    MAX_BYTES,
    checked_path,
    public_label,
    read_document,
    record_experiment,
    strict_json,
    validate_metadata,
)
from transcript_review_evaluation import summarize, words

ROOT = Path(__file__).resolve().parents[1]
WORKER = """
import asyncio,hashlib,json,sys
from dataclasses import asdict
from pathlib import Path
import httpx
from app.core.config import Settings
from app.domain.transcript_correction import POLICY_VERSION,validate_edits
from app.infrastructure.ollama_correction import OllamaCorrectionAdapter
from app.services.transcript_correction_ports import CorrectionContext
async def main():
    row=json.load(sys.stdin)
    settings=Settings()
    files=(Path('app/infrastructure/ollama_correction.py'),Path('app/domain/transcript_correction.py'))
    source_digest=hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()
    if source_digest != row['source_digest']: raise ValueError('source_changed')
    if settings.text_review_model_digest != row['model_digest']: raise ValueError('model_changed')
    context=CorrectionContext(row['original'],tuple(row['before']),tuple(row['after']),'tr')
    async with httpx.AsyncClient(trust_env=False,follow_redirects=False) as client:
        result=await OllamaCorrectionAdapter(settings,client).review(context)
    decision=validate_edits(row['original'],result.edits)
    print(json.dumps(dict(completed=True,suggested=decision.suggested_text,
        status=decision.status,edits=[asdict(e) for e in decision.edits],
        rejected_count=decision.rejected_count,model_name=result.model_name,
        model_digest=result.model_digest,policy_version=POLICY_VERSION,
        source_code_sha256=source_digest),ensure_ascii=True))
try: asyncio.run(main())
except Exception as error:
    code=getattr(error,'code','runner_error')
    allowed={'text_review_unavailable','text_review_model_mismatch','text_review_timeout',
        'text_review_invalid_response','text_review_context_limit'}
    print(json.dumps(dict(completed=False,error_code=code if code in allowed else 'runner_error')))
"""

SUGGESTION_WORKER = """
import asyncio,hashlib,json,sys
from pathlib import Path
import httpx
from app.core.config import Settings
from app.domain.transcript_suggestions import project_model_output
from app.infrastructure.ollama_correction import OllamaCorrectionAdapter
from app.services.transcript_correction_ports import CorrectionContext,ModelSelection
async def main():
    row=json.load(sys.stdin)
    files=tuple(Path('app')/name for name in ('infrastructure/ollama_correction.py',
        'domain/transcript_correction.py','domain/transcript_suggestions.py'))
    digest=lambda:hashlib.sha256(b''.join(path.read_bytes() for path in files)).hexdigest()
    source_digest=digest()
    if source_digest != row['source_digest']: raise ValueError('source_changed')
    context=CorrectionContext(row['original'],tuple(row['before']),tuple(row['after']),'tr')
    selected=ModelSelection(row['model_name'],row['model_digest'])
    async with httpx.AsyncClient(trust_env=False,follow_redirects=False) as client:
        result=await OllamaCorrectionAdapter(Settings(),client).suggest(context,selected)
    projection=project_model_output(row['original'],result.model_output,
        truncated=result.model_output_truncated)
    edits=[dict(start_char=p.start_char,end_char=p.end_char,original=p.original,
        replacement=p.replacement) for p in projection.proposals if p.start_char is not None]
    edits.sort(key=lambda edit:edit['start_char'])
    if digest()!=source_digest: raise ValueError('source_changed')
    print(json.dumps(dict(completed=True,suggested=projection.suggested_text,
        status=projection.status,edits=edits,
        rejected_count=sum(p.start_char is None for p in projection.proposals),
        model_name=result.model_name,model_digest=result.model_digest,
        policy_version='tr-context-words-v2',source_code_sha256=source_digest,
        model_output=result.model_output,model_output_truncated=result.model_output_truncated,
        saveable=projection.saveable,
        review_required_count=sum(p.assessment=='review_required' for p in projection.proposals)),
        ensure_ascii=True))
try: asyncio.run(main())
except Exception as error:
    code=getattr(error,'code','runner_error')
    allowed={'text_review_unavailable','text_review_model_mismatch','text_review_timeout',
        'text_review_invalid_response','text_review_context_limit'}
    print(json.dumps(dict(completed=False,error_code=code if code in allowed else 'runner_error')))
"""


def require(condition, code="invalid_review_input"):
    if not condition:
        raise ValueError(code)


def private_path(path):
    path = checked_path(checked_path(path).resolve())
    base = checked_path(checked_path(ROOT / "outputs").resolve())
    require(path != base and path.is_relative_to(base), "private_output_required")
    return path


def read_snapshot(path):
    with checked_path(path).open("rb") as stream:
        payload = stream.read(MAX_BYTES + 1)
    require(len(payload) <= MAX_BYTES, "input_limit")
    return strict_json(payload), hashlib.sha256(payload).hexdigest()


def validate_manifest(document):
    require(
        isinstance(document, dict)
        and document.keys()
        <= {
            "protocol",
            "reference_quality",
            "source_report_sha256",
            "selection",
            "cases",
        }
    )
    require(document.get("protocol") == "voiceup-context-review-v1")
    require(
        document.get("reference_quality")
        in {
            "synthetic-authored",
            "corpus-provided-not-listened",
            "unverified-meeting-reference",
        }
    )
    cases = document.get("cases")
    require(isinstance(cases, list) and 1 <= len(cases) <= 100)
    identities = set()
    for row in cases:
        require(
            isinstance(row, dict)
            and row.keys()
            <= {
                "id",
                "original",
                "reference",
                "before",
                "after",
                "source_sha256",
            }
        )
        require(all(isinstance(row.get(key), str) for key in ("original", "reference", "id")))
        require(0 < len(row["id"]) <= 120 and row["id"] not in identities)
        identities.add(row["id"])
        require(
            0 < len(row["original"]) <= 1024
            and len(row["reference"]) <= 4096
            and words(row["reference"])
        )
        require(
            all(
                isinstance(row.get(key), list)
                and len(row[key]) <= 3
                and all(isinstance(text, str) for text in row[key])
                for key in ("before", "after")
            )
        )
        require(sum(map(len, [row["original"], *row["before"], *row["after"]])) <= 4000)
        if "source_sha256" in row:
            require(
                isinstance(row["source_sha256"], str)
                and re.fullmatch(r"[a-f0-9]{64}", row["source_sha256"])
            )
    return cases


def save(path, value):
    path = private_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


def scoring_projection(result, original):
    """Retain all displayed text privately, but do not score an unsaveable partial answer as applied."""
    result = result.copy()
    result.setdefault("visible_suggested", result["suggested"])
    result.setdefault("visible_edits", result["edits"])
    if result["status"] in {"unmapped", "invalid_output"}:
        result["rejected_count"] += len(result["edits"])
        result.update(suggested=original, edits=[])
    return result


def prepare(args):
    private_path(args.output)
    if args.fixture:
        document = read_document(args.fixture)
        require(document.get("protocol") == "voiceup-context-review-v1")
    else:
        require(args.corpus is not None)
        require(type(args.per_stratum) is int and 1 <= args.per_stratum <= 50)
        data = read_document(args.corpus)
        require(
            data.get("status") == "complete"
            and data.get("protocol")
            in {"voiceup-mediaspeech-tr-expanded-v1", "voiceup-fleurs-tr-test-v1"}
        )
        selected = []
        eligible = [
            row
            for row in data["clips"]
            if 0 < len(row["hypothesis"]) <= 1024 and words(row["reference"])
        ]
        for clean in (True, False):
            group = sorted(
                (row for row in eligible if (row["metrics"]["cpwer"]["errors"] == 0) == clean),
                key=lambda row: row["source_sha256"],
            )
            require(len(group) >= args.per_stratum)
            selected.extend(group[: args.per_stratum])
        document = dict(
            protocol="voiceup-context-review-v1",
            reference_quality="corpus-provided-not-listened",
            source_report_sha256=hashlib.sha256(Path(args.corpus).read_bytes()).hexdigest(),
            selection=f"sha256-sorted-first-{args.per_stratum}-per-clean-and-error-stratum",
            cases=[
                dict(
                    id=f"clip-{index:03}",
                    source_sha256=row["source_sha256"],
                    original=row["hypothesis"],
                    reference=row["reference"],
                    before=[],
                    after=[],
                )
                for index, row in enumerate(selected, 1)
            ],
        )
    validate_manifest(document)
    save(args.output, document)
    print(f"Frozen {len(document['cases'])} cases; no model call.")


def run(args):
    output = private_path(args.output)
    manifest, input_digest = read_snapshot(args.input)
    cases = validate_manifest(manifest)
    metadata, _metadata_digest = read_snapshot(args.experiment_metadata)
    require(isinstance(metadata, dict), "invalid_metadata")
    experiment_id = public_label(metadata.get("experiment_id"))
    require("/" not in experiment_id, "invalid_experiment_id")
    validate_metadata({key: value for key, value in metadata.items() if key != "experiment_id"})
    require(len(metadata.get("models", [])) == 1 and metadata["pipeline"] == "transcript-review")
    require(
        metadata["language"] == "tr"
        and re.fullmatch(r"[a-f0-9]{64}", metadata["models"][0]["revision"])
    )
    require(
        metadata.get("dataset_revision") == input_digest
        and metadata.get("protocol_sha256") == input_digest,
        "input_changed",
    )
    selected_model = getattr(args, "visible_model", None)
    visible = selected_model is not None
    if visible:
        require(
            isinstance(selected_model, str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/:+-]{0,199}", selected_model)
            and metadata["models"][0]["id"] == "ollama/" + selected_model.replace(":", "-"),
            "invalid_selected_model",
        )
    files = [
        "app/backend/app/infrastructure/ollama_correction.py",
        "app/backend/app/domain/transcript_correction.py",
    ]
    if visible:
        files.append("app/backend/app/domain/transcript_suggestions.py")
    source_digest = hashlib.sha256(
        b"".join((ROOT / file).read_bytes() for file in files)
    ).hexdigest()
    require(metadata.get("configuration_sha256") == source_digest, "source_changed")
    require(not output.exists(), "existing_output")
    output.mkdir(parents=True)
    command = [
        args.bash,
        str(ROOT / "scripts/stack.sh"),
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        SUGGESTION_WORKER if visible else WORKER,
    ]
    environment = os.environ | {"MSYS2_ARG_CONV_EXCL": "*"}
    observations = []
    for index, row in enumerate(cases, 1):
        started = time.monotonic()
        try:
            process = subprocess.run(
                command,
                input=json.dumps(
                    {key: row[key] for key in ("original", "before", "after")}
                    | dict(
                        source_digest=source_digest, model_digest=metadata["models"][0]["revision"]
                    )
                    | ({"model_name": selected_model} if visible else {})
                ),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=115,
                env=environment,
                cwd=ROOT,
                check=False,
            )
            require(process.returncode == 0 and len(process.stdout) <= 65536, "runner_failed")
            result = strict_json(process.stdout)
            require(isinstance(result, dict) and type(result.get("completed")) is bool)
            if result["completed"]:
                require(
                    set(result)
                    == {
                        "completed",
                        "suggested",
                        "status",
                        "edits",
                        "rejected_count",
                        "model_name",
                        "model_digest",
                        "policy_version",
                        "source_code_sha256",
                    }
                    | (
                        {
                            "model_output",
                            "model_output_truncated",
                            "saveable",
                            "review_required_count",
                        }
                        if visible
                        else set()
                    )
                )
                require(
                    result["model_digest"] == metadata["models"][0]["revision"]
                    and result["source_code_sha256"] == source_digest
                    and result["policy_version"]
                    == ("tr-context-words-v2" if visible else "tr-context-words-v1")
                )
                if visible:
                    require(
                        result["model_name"] == selected_model
                        and result["status"]
                        in {"suggested", "unchanged", "unmapped", "invalid_output"}
                        and isinstance(result["model_output"], str)
                        and len(result["model_output"]) <= 8192
                        and type(result["model_output_truncated"]) is bool
                        and type(result["saveable"]) is bool
                        and type(result["review_required_count"]) is int
                        and 0 <= result["review_required_count"] <= len(result["edits"])
                    )
                    require(
                        not result["saveable"]
                        or (
                            result["status"] == "suggested"
                            and result["edits"]
                            and result["rejected_count"] == 0
                            and not result["model_output_truncated"]
                        )
                    )
                else:
                    require(result["status"] in {"suggested", "unchanged", "rejected"})
                    require((result["status"] == "suggested") == bool(result["edits"]))
                    require(result["status"] != "rejected" or result["rejected_count"] > 0)
                    require(result["status"] != "unchanged" or result["rejected_count"] == 0)
                summarize([dict(row, **result, elapsed_seconds=time.monotonic() - started)])
                if visible:
                    result = scoring_projection(result, row["original"])
            else:
                require(
                    set(result) == {"completed", "error_code"}
                    and result["error_code"]
                    in {
                        "text_review_unavailable",
                        "text_review_model_mismatch",
                        "text_review_timeout",
                        "text_review_invalid_response",
                        "text_review_context_limit",
                        "runner_error",
                    }
                )
        except (ValueError, OSError, subprocess.TimeoutExpired):
            result = dict(completed=False, error_code="runner_failed")
        if not result["completed"]:
            result.update(suggested=row["original"], edits=[], rejected_count=0)
        observed = dict(row, **result, elapsed_seconds=time.monotonic() - started)
        observations.append(observed)
        save(output / f"row-{index:03}.private.json", observed)
        print(
            f"Row {index}/{len(cases)}: {'completed' if result['completed'] else result['error_code']}; {observed['elapsed_seconds']:.2f}s",
            flush=True,
        )
    public = dict(
        protocol="voiceup-context-review-visible-v1" if visible else "voiceup-context-review-v1",
        status="complete",
        reference_quality=manifest["reference_quality"],
        input_sha256=input_digest,
        metrics=summarize(observations),
        configuration_sha256=source_digest,
        model_digest=metadata["models"][0]["revision"],
    )
    if visible:
        public.update(
            policy_version="tr-context-words-v2",
            model_name=selected_model,
            review_required_edits=sum(row.get("review_required_count", 0) for row in observations),
            saveable_rows=sum(row.get("saveable", False) for row in observations),
            visible_status_counts={
                status: sum(row.get("status") == status for row in observations)
                for status in ("unchanged", "suggested", "unmapped", "invalid_output")
            },
        )
    save(output / "aggregate.json", public)
    record_experiment(
        args.results_md,
        experiment_id=experiment_id,
        metadata={key: value for key, value in metadata.items() if key != "experiment_id"},
        report=public,
        kind="transcript_review",
    )
    print("Paired scores saved and experiment recorded; private text excluded.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser("prepare")
    source = preparation.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture", type=Path)
    source.add_argument("--corpus", type=Path)
    preparation.add_argument("--per-stratum", type=int, default=6)
    preparation.add_argument("--output", type=Path, required=True)
    evaluation = commands.add_parser("run")
    evaluation.add_argument("--input", type=Path, required=True)
    evaluation.add_argument("--output", type=Path, required=True)
    evaluation.add_argument("--experiment-metadata", type=Path, required=True)
    evaluation.add_argument("--results-md", type=Path, default=ROOT / "results.md")
    evaluation.add_argument(
        "--visible-model",
        help="Exact installed Ollama name; use the separate visible-proposal policy and provenance.",
    )
    evaluation.add_argument(
        "--bash", default=r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else "bash"
    )
    args = parser.parse_args()
    (prepare if args.command == "prepare" else run)(args)


if __name__ == "__main__":
    main()
