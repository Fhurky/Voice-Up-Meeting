"""Source-time ownership and unique clean evidence for uploaded meetings."""

import hashlib
import math

UPLOAD_PART_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024 * 1024
MAX_SOURCE_SECONDS = 4 * 3600
CORE_SECONDS = 300
CONTEXT_SECONDS = 5
AUTO_ENROLL_SECONDS = 20
# A few seconds of clean speech cannot carry a person's name, however similar they sound.
MIN_RECOGNITION_SECONDS = 10
# Longest recording diarized in one pass (PRD 030). Two hours peaked at 4.3 GiB in the speech
# service; four hours need 6.6 GiB, more than a 7.35 GB local Docker VM holds beside the stack.
WHOLE_RECORDING_MAX_SECONDS = 120 * 60
# A turn shorter than a millisecond after clipping to a window carries no speech.
MIN_WINDOW_TURN_SECONDS = 0.001

# Two-channel capture (PRD 037): channel 0 is the recording computer's microphone, channel 1 the
# system audio of its shared screen. The browser streams interleaved PCM16 parts during the meeting.
CAPTURE_MODES = ("file", "two_channel")
CAPTURE_CHANNELS = 2
CAPTURE_FRAME_BYTES = CAPTURE_CHANNELS * 2
CAPTURE_HEADER_BYTES = 44
# Browser parts are two seconds; four seconds of audio bounds any accepted part.
CAPTURE_PART_MAX_SECONDS = 4
# Without a part for this long, the owner may process what arrived.
CAPTURE_IDLE_SECONDS = 120
CAPTURE_CHAIN_START = "0" * 64
CHANNEL_NAMES = {0: "microphone", 1: "system"}


def capture_max_frames(sample_rate: int, max_seconds: int, max_bytes: int) -> int:
    """Frames a capture may hold under the duration and source byte limits."""
    return min(sample_rate * max_seconds, (max_bytes - CAPTURE_HEADER_BYTES) // CAPTURE_FRAME_BYTES)


def capture_frames(stored_bytes: int) -> int:
    """Frames received so far; the header space is reserved from the first byte."""
    return max(0, (stored_bytes - CAPTURE_HEADER_BYTES) // CAPTURE_FRAME_BYTES)


def next_capture_chain(chain: str, part_sha256: str) -> str:
    """`chain_n = SHA-256(chain_{n-1} || SHA-256(part_n))`; the browser computes the same value."""
    return hashlib.sha256(bytes.fromhex(chain) + bytes.fromhex(part_sha256)).hexdigest()


def capture_wav_header(sample_rate: int, frames: int) -> bytes:
    """Canonical 44-byte header for interleaved two-channel PCM16."""
    data = frames * CAPTURE_FRAME_BYTES
    return (
        b"RIFF"
        + (36 + data).to_bytes(4, "little")
        + b"WAVEfmt "
        + (16).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + CAPTURE_CHANNELS.to_bytes(2, "little")
        + sample_rate.to_bytes(4, "little")
        + (sample_rate * CAPTURE_FRAME_BYTES).to_bytes(4, "little")
        + CAPTURE_FRAME_BYTES.to_bytes(2, "little")
        + (16).to_bytes(2, "little")
        + b"data"
        + data.to_bytes(4, "little")
    )


def window_turns(
    turns: list[tuple[float, float, str]], start: float, end: float
) -> list[dict[str, float | str]]:
    """Meeting turns inside one analysis window, in seconds from the window start."""
    rows: list[dict[str, float | str]] = []
    for first, last, speaker in turns:
        begin, finish = max(first, start), min(last, end)
        if finish - begin >= MIN_WINDOW_TURN_SECONDS:
            rows.append({"start": begin - start, "end": finish - start, "speaker": speaker})
    return rows


def window_core_seconds(props: dict[str, object]) -> int:
    """Historical checkpoints predate the explicit per-meeting window policy."""
    value = props.get("window_core_seconds", 60)
    if type(value) is not int or value not in {60, CORE_SECONDS}:
        raise ValueError("Invalid core duration")
    return value


def analysis_windows(
    duration: float, *, core_seconds: int = CORE_SECONDS
) -> list[tuple[int, float, float, float, float]]:
    if not math.isfinite(duration) or not 0 < duration <= MAX_SOURCE_SECONDS:
        raise ValueError("Invalid source duration")
    if type(core_seconds) is not int or core_seconds not in {60, CORE_SECONDS}:
        raise ValueError("Invalid core duration")
    return [
        (
            index,
            max(0.0, index * core_seconds - CONTEXT_SECONDS),
            float(index * core_seconds),
            min(duration, (index + 1) * core_seconds),
            min(duration, (index + 1) * core_seconds + CONTEXT_SECONDS),
        )
        for index in range(math.ceil(duration / core_seconds))
    ]


Window = tuple[int, float, float, float, float]


def meeting_tracks(capture_mode: str) -> tuple[int | None, ...]:
    """Source channels analysed separately: both channels of a capture, else one mixed track."""
    return (0, 1) if capture_mode == "two_channel" else (None,)


def track_windows(
    duration: float, tracks: tuple[int | None, ...], *, core_seconds: int = CORE_SECONDS
) -> list[tuple[Window, int | None]]:
    """Analysis chunks in processing order with their channel.

    Channels alternate inside each time window, so the transcript fills in time order and the
    chunk index stays a single durable progress counter.
    """
    chunks: list[tuple[Window, int | None]] = []
    for _, context_start, core_start, core_end, context_end in analysis_windows(
        duration, core_seconds=core_seconds
    ):
        for channel in tracks:
            chunks.append(
                ((len(chunks), context_start, core_start, core_end, context_end), channel)
            )
    return chunks


def previous_track_chunk(chunks: list[tuple[Window, int | None]], index: int) -> int | None:
    """The preceding chunk of the same channel, whose pending words continue into this one."""
    channel = chunks[index][1]
    return next(
        (position for position in range(index - 1, -1, -1) if chunks[position][1] == channel),
        None,
    )


def clean_union(
    ranges: list[tuple[int, int]],
    excluded: list[tuple[int, int]],
    start: int,
    end: int,
) -> list[tuple[int, int]]:
    """Union integer sample ranges, intersect ownership, then subtract all overlap."""
    if start < 0 or end < start:
        raise ValueError("Invalid source bounds")
    for left, right in ranges + excluded:
        if not isinstance(left, int) or not isinstance(right, int) or left < 0 or right <= left:
            raise ValueError("Invalid sample interval")
    merged: list[tuple[int, int]] = []
    for left, right in sorted(ranges):
        left, right = max(start, left), min(end, right)
        if left >= right:
            continue
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    for left, right in sorted(excluded):
        result: list[tuple[int, int]] = []
        for begin, finish in merged:
            if right <= begin or left >= finish:
                result.append((begin, finish))
            else:
                if begin < left:
                    result.append((begin, left))
                if right < finish:
                    result.append((right, finish))
        merged = result
    return merged
