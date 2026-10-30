"""Persist one source-owned core and reconcile its independently qualified acoustic evidence."""

import asyncio
import json
import math
from dataclasses import asdict
from datetime import UTC, datetime

from app.core.config import Settings
from app.domain.meeting import clean_union
from app.domain.meeting_candidates import (
    CandidateTurn,
    build_candidate_contexts,
    native_overlap_ranges,
)
from app.domain.meeting_centroid import ABSENT_RESULTANT, advance_centroid
from app.domain.meeting_identity import (
    AcousticCandidate,
    choose_acoustic_track,
    normalized_evidence,
)
from app.domain.meeting_native_exclusions import (
    ABSENT_EXCLUSIONS,
    check_exclusion_graph,
    link_native_peers,
    separation_score,
)
from app.domain.meeting_reconciliation import (
    ReconciliationResult,
    ReconciliationTrack,
    reconcile_tracks,
)
from app.domain.meeting_timeline import (
    SpeechTurn,
    SpeechWord,
    align_words,
    committed_turns,
    stitch_words,
)
from app.domain.models.meeting import Meeting, MeetingChunk, MeetingSpeaker, MeetingTranscript
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION, MatchPolicy
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.services.meeting_ports import MeetingChunkResult, MeetingTurn
from app.services.speaker_ports import SpeakerError

RECONCILIATION_VERSION = "meeting-track-reconciliation-v1"


class TrackRebuild:
    """Forced identities for one reconciliation pass; existing rows are reused in ordinal order."""

    def __init__(self, result: ReconciliationResult) -> None:
        self.result = result
        self.rows: dict[int, MeetingSpeaker] = {}

    def identity(self, index: int, label: str) -> int | None:
        row = self.rows.get(self.result.clusters[(index, label)])
        return row.meeting_speaker_id if row is not None else None

    def adopted(self) -> set[int]:
        return {row.meeting_speaker_id for row in self.rows.values()}

    def adopt(self, index: int, label: str, row: MeetingSpeaker, reason: str | None) -> None:
        cluster = self.result.clusters[(index, label)]
        self.rows[cluster] = row
        row.reason = reason
        row.props = {**row.props, "reconciliation_ambiguous": cluster in self.result.ambiguous}


def intersections(first: list[tuple[int, int]], second: list[tuple[int, int]]) -> int:
    rows = [(max(a, c), min(b, d)) for a, b in first for c, d in second if max(a, c) < min(b, d)]
    return sum(
        end - start
        for start, end in clean_union(rows, [], 0, max((end for _, end in rows), default=0))
    )


class MeetingChunkPersistence:
    def __init__(self, settings: Settings) -> None:
        self.policy = MatchPolicy(
            settings.speaker_match_threshold,
            settings.speaker_new_threshold,
            settings.speaker_match_margin,
        )
        self.reconciliation_threshold = settings.meeting_reconciliation_threshold

    async def reconcile(self, repository: MeetingRepository, meeting: Meeting) -> None:
        """Rebuild speakers and lines from durable chunk results with one identity per voice."""
        if meeting.sample_rate is None or meeting.duration_seconds is None:
            raise SpeakerError("recording_unavailable", 410)
        rate = meeting.sample_rate
        chunks = await repository.chunks(meeting.tenant_id, meeting.meeting_id)
        results = [
            (chunk, MeetingChunkResult.model_validate(chunk.result.get("provider")))
            for chunk in chunks
        ]
        tracks: list[ReconciliationTrack] = []
        conflicts: list[tuple[tuple[int, str], tuple[int, str]]] = []
        for chunk, result in results:
            first, last = round(float(chunk.core_start) * rate), round(float(chunk.core_end) * rate)
            speech = {
                track.speaker: clean_union(
                    [
                        (
                            round((float(chunk.context_start) + turn.start) * rate),
                            round((float(chunk.context_start) + turn.end) * rate),
                        )
                        for turn in result.turns
                        if turn.speaker == track.speaker
                    ],
                    [],
                    0,
                    round(meeting.duration_seconds * rate),
                )
                for track in result.tracks
            }
            for position, track in enumerate(result.tracks):
                owned = clean_union(speech[track.speaker], [], first, last)
                # Simultaneous speech or independent voice evidence proves two different people.
                for other in result.tracks[:position]:
                    if intersections(speech[track.speaker], speech[other.speaker]) > 0 or (
                        track.status == "usable"
                        and other.status == "usable"
                        and separation_score(track.embedding, other.embedding, self.policy)
                        is not None
                    ):
                        conflicts.append(
                            ((chunk.index, other.speaker), (chunk.index, track.speaker))
                        )
                tracks.append(
                    ReconciliationTrack(
                        chunk.index,
                        track.speaker,
                        sum(end - start for start, end in owned) / rate,
                        (
                            tuple(normalized_evidence(track.tracking.embedding, dimensions=256))
                            if track.tracking is not None
                            else None
                        ),
                    )
                )
        meeting.props = {**meeting.props, "reconciliation_version": RECONCILIATION_VERSION}
        if len(chunks) < 2 or all(track.embedding is None for track in tracks):
            return
        outcome = await asyncio.to_thread(
            reconcile_tracks,
            tracks,
            self.reconciliation_threshold,
            self.policy.new_threshold,
            conflicts,
        )
        rows, _ = await repository.speakers(meeting.tenant_id, meeting.meeting_id, 0, 1001)
        for row in rows:
            row.display_name, row.profile_id, row.reason = None, None, None
            row.decision, row.speech_seconds, row.clean_ranges = "profile_pending", 0, []
            row.embedding, row.model_id, row.model_revision = None, None, None
            row.tracking_embedding, row.tracking_model_id = None, None
            row.tracking_model_revision, row.source_sha256 = None, None
            row.props = {}
        now = datetime.now(UTC)
        await repository.retire_transcript(
            meeting.tenant_id, meeting.meeting_id, meeting.created_by, now
        )
        rebuild = TrackRebuild(outcome)
        for chunk, result in results:
            await self.persist(
                repository,
                meeting,
                (
                    chunk.index,
                    float(chunk.context_start),
                    float(chunk.core_start),
                    float(chunk.core_end),
                    float(chunk.context_end),
                ),
                result,
                rebuild=rebuild,
            )
        adopted = rebuild.adopted()
        for row in rows:
            if row.meeting_speaker_id not in adopted:
                row.is_deleted, row.deleted_at, row.deleted_by = True, now, meeting.created_by
        await repository.session.flush()

    async def persist(
        self,
        repository: MeetingRepository,
        meeting: Meeting,
        window: tuple[int, float, float, float, float],
        result: MeetingChunkResult,
        *,
        rebuild: TrackRebuild | None = None,
    ) -> None:
        index, context_start, core_start, core_end, context_end = window
        if abs(result.input_seconds - (context_end - context_start)) > 1 / 8000:
            raise SpeakerError("model_mismatch", 502)
        if meeting.sample_rate is None or meeting.duration_seconds is None:
            raise SpeakerError("recording_unavailable", 410)
        rate = meeting.sample_rate
        first, last = round(core_start * rate), round(core_end * rate)
        source_end = round(meeting.duration_seconds * rate)
        rows, total = await repository.speakers(meeting.tenant_id, meeting.meeting_id, 0, 1001)
        if total > 1000:
            raise SpeakerError("audio_limit", 413)
        try:
            native_graph = check_exclusion_graph(
                [
                    (row.meeting_speaker_id, row.props.get("native_exclusions", ABSENT_EXCLUSIONS))
                    for row in rows
                ],
                meeting.source_sha256,
            )
        except (TypeError, ValueError) as exc:
            raise SpeakerError("model_mismatch", 502) from exc
        native_tracks = {track.speaker: track for track in result.tracks}
        by_id = {row.meeting_speaker_id: row for row in rows}
        mapped: dict[str, MeetingSpeaker] = {}
        local_ranges = {
            track.speaker: clean_union(
                [
                    (
                        round((context_start + turn.start) * rate),
                        round((context_start + turn.end) * rate),
                    )
                    for turn in result.turns
                    if turn.speaker == track.speaker
                    and round((context_start + turn.start) * rate)
                    < round((context_start + turn.end) * rate)
                ],
                [],
                0,
                source_end,
            )
            for track in result.tracks
        }
        for track in result.tracks:
            speech = local_ranges[track.speaker]
            owned = clean_union(speech, [], first, last)
            vector = normalized_evidence(track.embedding) if track.embedding is not None else None
            tracking = track.tracking
            tracking_vector = (
                normalized_evidence(tracking.embedding, dimensions=256)
                if tracking is not None
                else None
            )
            overlapping = {
                row.meeting_speaker_id
                for label, row in mapped.items()
                if intersections(speech, local_ranges[label]) > 0
            }
            native_differences: dict[int, tuple[str, float]] = {}
            if track.status == "usable" and vector is not None:
                for label, previous_row in mapped.items():
                    other = native_tracks[label]
                    if other.status != "usable":
                        continue
                    score = separation_score(vector, other.embedding, self.policy)
                    if score is not None:
                        native_differences.setdefault(
                            previous_row.meeting_speaker_id, (label, score)
                        )
            overlapping.update(native_differences)
            if rebuild is not None:
                identity, reason = rebuild.identity(index, track.speaker), "reconciled"
            elif tracking is not None:
                candidates = [
                    AcousticCandidate(row.meeting_speaker_id, list(row.tracking_embedding))
                    for row in rows
                    if row.tracking_embedding is not None
                    and row.tracking_model_id == tracking.model_id
                    and row.tracking_model_revision == tracking.model_revision
                ]
                identity, reason = choose_acoustic_track(
                    tracking_vector, candidates, overlapping, self.policy, dimensions=256
                )
            else:
                candidates = [
                    AcousticCandidate(row.meeting_speaker_id, list(row.embedding))
                    for row in rows
                    if row.embedding is not None
                    and row.model_id == MODEL_ID
                    and row.model_revision == MODEL_REVISION
                ]
                identity, reason = choose_acoustic_track(
                    vector, candidates, overlapping, self.policy
                )
            # The shared source context can reconnect an otherwise short local track.
            # Require a unique, non-overlapped same-source interval, never a name/count.
            context = clean_union(speech, [], max(0, round(context_start * rate)), first)
            if rebuild is None and identity is None and context:
                anchors = sorted(
                    [
                        (
                            intersections(
                                context, [(a, b) for a, b in row.props.get("speech_ranges", [])]
                            ),
                            row.meeting_speaker_id,
                        )
                        for row in rows
                        if row.meeting_speaker_id not in overlapping
                    ],
                    reverse=True,
                )
                if (
                    anchors
                    and anchors[0][0] >= 0.3 * rate
                    and anchors[0][0] >= 0.8 * sum(b - a for a, b in context)
                    and (len(anchors) == 1 or anchors[1][0] < 0.1 * anchors[0][0])
                ):
                    candidate = next(row for row in rows if row.meeting_speaker_id == anchors[0][1])
                    if tracking is not None and candidate.tracking_embedding is not None:
                        compatible = (
                            candidate.tracking_model_id == tracking.model_id
                            and candidate.tracking_model_revision == tracking.model_revision
                            and sum(
                                a * b
                                for a, b in zip(
                                    tracking_vector or [],
                                    normalized_evidence(
                                        list(candidate.tracking_embedding), dimensions=256
                                    ),
                                    strict=True,
                                )
                            )
                            >= self.policy.match_threshold
                        )
                    else:
                        compatible = (
                            vector is None
                            or candidate.embedding is None
                            or sum(
                                a * b
                                for a, b in zip(
                                    vector,
                                    normalized_evidence(list(candidate.embedding)),
                                    strict=True,
                                )
                            )
                            >= self.policy.match_threshold
                        )
                    if compatible:
                        identity, reason = candidate.meeting_speaker_id, "source_context"
            row = next((row for row in rows if row.meeting_speaker_id == identity), None)
            if not owned and row is None:
                continue
            if row is None and rebuild is not None:
                adopted = rebuild.adopted()
                row = next(
                    (value for value in rows if value.meeting_speaker_id not in adopted), None
                )
                if row is not None:
                    rebuild.adopt(
                        index, track.speaker, row, track.status if vector is None else reason
                    )
            if row is None:
                if len(rows) >= 1000:
                    raise SpeakerError("audio_limit", 413)
                row = MeetingSpeaker(
                    tenant_id=meeting.tenant_id,
                    meeting_id=meeting.meeting_id,
                    ordinal=max((value.ordinal for value in rows), default=-1) + 1,
                    reason=track.status if vector is None else reason,
                    speech_seconds=0,
                    props={
                        "reconciliation_ambiguous": reason
                        in {"insufficient_margin", "below_match_threshold", "overlap_conflict"}
                    },
                    clean_ranges=[],
                    created_by=meeting.created_by,
                    updated_by=meeting.created_by,
                )
                repository.session.add(row)
                await repository.session.flush()
                rows.append(row)
                by_id[row.meeting_speaker_id] = row
                native_graph[row.meeting_speaker_id] = None
                if rebuild is not None:
                    rebuild.adopt(index, track.speaker, row, row.reason)
            try:
                for peer_id, (label, score) in native_differences.items():
                    if meeting.source_sha256 is None:
                        raise ValueError("missing_native_source")
                    link_native_peers(
                        native_graph,
                        row.meeting_speaker_id,
                        peer_id,
                        source_sha256=meeting.source_sha256,
                        chunk_index=index,
                        labels=(track.speaker, label),
                        recipe=result.model_identity.diarization.recipe,
                        similarity=score,
                        new_threshold=self.policy.new_threshold,
                    )
                    for owner in (row.meeting_speaker_id, peer_id):
                        state = native_graph[owner]
                        if state is None:
                            raise ValueError("missing_native_exclusion")
                        by_id[owner].props = {
                            **by_id[owner].props,
                            "native_exclusions": state.to_record(),
                        }
            except (TypeError, ValueError) as exc:
                raise SpeakerError("model_mismatch", 502) from exc
            if not owned:
                mapped[track.speaker] = row
                continue
            previous_seconds = row.speech_seconds
            ranges = clean_union(
                [
                    (
                        math.ceil((context_start + span.start) * rate),
                        math.floor((context_start + span.end) * rate),
                    )
                    for span in track.validated_ranges
                    if math.ceil((context_start + span.start) * rate)
                    < math.floor((context_start + span.end) * rate)
                ],
                [],
                first,
                last,
            )
            combined = clean_union(
                [(a, b) for a, b in row.clean_ranges] + ranges, [], 0, source_end
            )
            seconds = sum(end - start for start, end in combined) / rate
            new_seconds = seconds - previous_seconds
            resultant_props: dict[str, object] = {}
            try:
                centroid = advance_centroid(
                    list(row.embedding) if row.embedding is not None else None,
                    previous_seconds,
                    vector,
                    new_seconds,
                    row.props.get("embedding_resultant", ABSENT_RESULTANT),
                )
            except (ValueError, TypeError, OverflowError) as exc:
                raise SpeakerError("model_mismatch", 502) from exc
            if new_seconds > 0 and vector is not None:
                if centroid.embedding is None or centroid.state is None:
                    raise SpeakerError("model_mismatch", 502)
                row.embedding = centroid.embedding
                resultant_props["embedding_resultant"] = centroid.state.to_record()
                row.model_id, row.model_revision, row.source_sha256 = (
                    MODEL_ID,
                    MODEL_REVISION,
                    meeting.source_sha256,
                )
            row.clean_ranges, row.speech_seconds = [[a, b] for a, b in combined], seconds
            previous_speech = [(a, b) for a, b in row.props.get("speech_ranges", [])]
            speech_ranges = clean_union(previous_speech + owned, [], 0, source_end)
            new_tracking_seconds = (
                sum(b - a for a, b in speech_ranges) - sum(b - a for a, b in previous_speech)
            ) / rate
            tracking_seconds = float(row.props.get("tracking_seconds", 0))
            try:
                tracking_centroid = advance_centroid(
                    list(row.tracking_embedding) if row.tracking_embedding is not None else None,
                    tracking_seconds,
                    tracking_vector,
                    new_tracking_seconds,
                    row.props.get("tracking_resultant", ABSENT_RESULTANT),
                    dimensions=256,
                )
            except (ValueError, TypeError, OverflowError) as exc:
                raise SpeakerError("model_mismatch", 502) from exc
            if tracking is not None and tracking_vector is not None and new_tracking_seconds > 0:
                if tracking_centroid.embedding is None or tracking_centroid.state is None:
                    raise SpeakerError("model_mismatch", 502)
                row.tracking_embedding = tracking_centroid.embedding
                resultant_props["tracking_resultant"] = tracking_centroid.state.to_record()
                row.tracking_model_id = tracking.model_id
                row.tracking_model_revision = tracking.model_revision
                tracking_seconds += new_tracking_seconds
            row.props = {
                **row.props,
                **resultant_props,
                "speech_ranges": [[a, b] for a, b in speech_ranges],
                "tracking_seconds": tracking_seconds,
            }
            if result.vad is None and track.candidate_contexts is not None:
                row.source_sha256 = meeting.source_sha256
                contexts = list(row.props.get("candidate_contexts", []))
                for source_candidate in track.candidate_contexts if tracking is not None else []:
                    begin = max(first, math.ceil((context_start + source_candidate.start) * rate))
                    finish = min(last, math.floor((context_start + source_candidate.end) * rate))
                    if finish - begin < 3 * rate:
                        continue
                    voiced = clean_union(
                        [
                            (
                                math.ceil((context_start + span.start) * rate),
                                math.floor((context_start + span.end) * rate),
                            )
                            for span in source_candidate.voiced_ranges
                            if math.ceil((context_start + span.start) * rate)
                            < math.floor((context_start + span.end) * rate)
                        ],
                        [],
                        begin,
                        finish,
                    )
                    if voiced and not any(
                        max(begin, previous["start"]) < min(finish, previous["end"])
                        for previous in contexts
                    ):
                        contexts.append(
                            {
                                "start": begin,
                                "end": finish,
                                "voiced_ranges": [[a, b] for a, b in voiced],
                            }
                        )
                contexts.sort(key=lambda value: value["start"])
                contexts = contexts[:256]
                row.props = {
                    **row.props,
                    "candidate_contexts": contexts,
                    "candidate_version": "meeting-natural-context-v1",
                }
            mapped[track.speaker] = row

        if result.vad is not None:
            source_turns = [
                CandidateTurn(
                    math.ceil((context_start + turn.start) * rate),
                    math.floor((context_start + turn.end) * rate),
                    (
                        mapped[turn.speaker].meeting_speaker_id
                        if turn.speaker in mapped
                        else -(number + 1)
                    ),
                    turn.speaker,
                )
                for number, turn in enumerate(result.turns)
                if math.ceil((context_start + turn.start) * rate)
                < math.floor((context_start + turn.end) * rate)
            ]
            source_vad = clean_union(
                [
                    (
                        math.ceil((context_start + span.start) * rate),
                        math.floor((context_start + span.end) * rate),
                    )
                    for span in result.vad.ranges
                    if math.ceil((context_start + span.start) * rate)
                    < math.floor((context_start + span.end) * rate)
                ],
                [],
                0,
                source_end,
            )
            overlap = native_overlap_ranges(source_turns)
            owned_ids = {
                turn.speaker
                for turn in source_turns
                if turn.speaker > 0 and max(first, turn.start) < min(last, turn.end)
            }
            for row in rows:
                if row.meeting_speaker_id not in owned_ids:
                    continue
                candidates_after_mapping = (
                    build_candidate_contexts(
                        source_turns,
                        source_vad,
                        row.meeting_speaker_id,
                        rate,
                        first,
                        last,
                        native_overlap=overlap,
                    )
                    if row.tracking_embedding is not None
                    else []
                )
                contexts = list(row.props.get("candidate_contexts", []))
                for candidate_context in candidates_after_mapping:
                    if any(
                        max(candidate_context.start, previous["start"])
                        < min(candidate_context.end, previous["end"])
                        for previous in contexts
                    ):
                        continue
                    contexts.append(
                        {
                            "start": candidate_context.start,
                            "end": candidate_context.end,
                            "voiced_ranges": [[a, b] for a, b in candidate_context.voiced_ranges],
                        }
                    )
                contexts.sort(key=lambda value: value["start"])
                row.source_sha256 = meeting.source_sha256
                row.props = {
                    **row.props,
                    "candidate_contexts": contexts[:256],
                    "candidate_version": "meeting-natural-context-v1",
                }

        def turns(sequence: list[MeetingTurn]) -> list[SpeechTurn]:
            return [
                SpeechTurn(
                    context_start + turn.start,
                    context_start + turn.end,
                    (
                        mapped[turn.speaker].meeting_speaker_id
                        if turn.speaker in mapped
                        else -(number + 1)
                    ),
                )
                for number, turn in enumerate(sequence)
            ]

        words = [
            SpeechWord(
                context_start + word.start,
                context_start + word.end,
                word.word,
                word.probability,
            )
            for word in result.words
        ]
        regular, exclusive = turns(result.turns), turns(result.exclusive_turns)
        if index:
            previous = await repository.chunk(meeting.tenant_id, meeting.meeting_id, index - 1)
            if previous is None or previous.result.get("checkpoint_version") != 1:
                raise SpeakerError("model_mismatch", 502)
            previous_words = [SpeechWord(**value) for value in previous.result["pending_words"]]
            previous_provider = previous.result.get("provider")
            # Automatic language requires agreement across the actual neighboring observations.
            turkish = meeting.language == "tr" or (
                meeting.language == "auto"
                and result.language == "tr"
                and isinstance(previous_provider, dict)
                and previous_provider.get("language") == "tr"
            )
            words = stitch_words(
                previous_words, words, core_start, language="tr" if turkish else None
            )
            regular = [SpeechTurn(**value) for value in previous.result["pending_turns"]] + regular
            exclusive = [
                SpeechTurn(**value) for value in previous.result["pending_exclusive"]
            ] + exclusive
        # Delay only the unresolved boundary, not the complete meeting transcript.
        commit_start = max(0.0, core_start - 5)
        commit_end = core_end if core_end == meeting.duration_seconds else core_end - 5
        lines = align_words(words, regular, exclusive, commit_start, commit_end)
        checkpoint = {
            "checkpoint_version": 1,
            "provider": result.model_dump(mode="json"),
            "pending_words": (
                [asdict(word) for word in words if (word.start + word.end) / 2 >= commit_end]
                if commit_end < meeting.duration_seconds
                else []
            ),
            "pending_turns": (
                [asdict(turn) for turn in regular if turn.end > commit_end]
                if commit_end < meeting.duration_seconds
                else []
            ),
            "pending_exclusive": (
                [asdict(turn) for turn in exclusive if turn.end > commit_end]
                if commit_end < meeting.duration_seconds
                else []
            ),
            "committed_until": commit_end,
            # Mapped regular turns for this chunk's commit window; local labels alone
            # cannot be re-attributed to meeting speakers after the chunk is persisted.
            "speaker_turns": [
                asdict(turn) for turn in committed_turns(regular, commit_start, commit_end)
            ],
        }
        if (
            len(json.dumps(checkpoint, separators=(",", ":"), ensure_ascii=False).encode())
            > 8 * 1024 * 1024
        ):
            raise SpeakerError("model_mismatch", 502)
        ordinal = await repository.next_transcript_ordinal(meeting.tenant_id, meeting.meeting_id)
        for number, line in enumerate(lines):
            repository.session.add(
                MeetingTranscript(
                    tenant_id=meeting.tenant_id,
                    meeting_id=meeting.meeting_id,
                    meeting_speaker_id=(
                        line.speaker if line.speaker is not None and line.speaker > 0 else None
                    ),
                    ordinal=ordinal + number,
                    start=max(0, line.start),
                    end=min(meeting.duration_seconds, line.end),
                    text=line.text,
                    language=result.language or meeting.language,
                    overlap=line.overlap,
                    uncertain=line.uncertain or line.speaker is None or line.speaker < 0,
                    created_by=meeting.created_by,
                    updated_by=meeting.created_by,
                )
            )
        if rebuild is not None:
            stored = await repository.chunk(meeting.tenant_id, meeting.meeting_id, index)
            if stored is None:
                raise SpeakerError("model_mismatch", 502)
            stored.result = checkpoint
        else:
            repository.session.add(
                MeetingChunk(
                    tenant_id=meeting.tenant_id,
                    meeting_id=meeting.meeting_id,
                    index=index,
                    context_start=context_start,
                    core_start=core_start,
                    core_end=core_end,
                    context_end=context_end,
                    status="succeeded",
                    result=checkpoint,
                    created_by=meeting.created_by,
                    updated_by=meeting.created_by,
                )
            )
        await repository.session.flush()
