"""Generated meeting types must preserve fields whose names resemble schema metadata."""

from pathlib import Path

from app.scripts.export_openapi import _canonicalize, export_openapi


def test_meeting_title_survives_offline_export(tmp_path: Path) -> None:
    schemas = export_openapi(tmp_path / "contract.json")["components"]["schemas"]
    for name in ("MeetingCreate", "MeetingResponse"):
        assert schemas[name]["properties"]["title"]["type"] == "string"
    assert "speaker_ordinal" in schemas["MeetingTranscriptResponse"]["properties"]


def test_schema_metadata_does_not_delete_payload_property_names() -> None:
    schema = {
        "title": "A schema",
        "properties": {
            "title": {"type": "string", "title": "Title"},
            "operationId": {"type": "string"},
        },
        "example": {"title": "User title", "operationId": "User value"},
    }
    result = _canonicalize(schema)
    assert "title" not in result
    assert result["properties"] == {"operationId": {"type": "string"}, "title": {"type": "string"}}
    assert result["example"] == schema["example"]


def test_natural_candidates_are_distinct_from_verified_voice():
    from app.services.meeting_ports import MeetingCandidateContext, MeetingTrack

    candidate = MeetingCandidateContext(
        start=0.0, end=7.0, voiced_ranges=[{"start": 0.5, "end": 2.0}]
    )
    track = MeetingTrack(
        speaker="a",
        status="inconsistent_audio",
        embedding=None,
        dimensions=192,
        validated_ranges=[],
        validated_seconds=0.0,
        used_seconds=0.0,
        windows_count=0,
        min_pair_similarity=None,
        preprocessing_version="vad-windows-v1",
        candidate_contexts=[candidate],
    )
    assert track.validated_seconds == 0
    assert track.candidate_contexts == [candidate]
