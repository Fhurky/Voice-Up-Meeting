"""Packed sample provenance stays inside the original disjoint source frames."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.meeting_samples import (
    SourceFrameManifest,
    map_provider_ranges,
    select_source_ranges,
)


def test_sample_selection_takes_first_sixty_seconds_without_source_gaps() -> None:
    assert select_source_ranges(((8000, 168000), (240000, 640000)), 800000, 8000) == (
        (8000, 168000),
        (240000, 560000),
    )


def test_manifest_is_immutable_and_exposes_exact_source_duration() -> None:
    manifest = SourceFrameManifest(8000, 300000, ((0, 80000), (160000, 240000)))
    assert manifest.frames == 160000 and manifest.seconds == 20
    with pytest.raises(FrozenInstanceError):
        manifest.sample_rate = 16000


@pytest.mark.parametrize(
    ("rate", "first", "last", "expected"),
    [
        (8000, 1601, 400003, ((801, 200001),)),
        (24000, 1603, 400001, ((2405, 600001),)),
        (44100, 1603, 400001, ((4419, 1102502),)),
    ],
)
def test_provider_mapping_crops_fractional_source_samples_inward(
    rate: int, first: int, last: int, expected: tuple[tuple[int, int], ...]
) -> None:
    manifest = SourceFrameManifest(rate, 30 * rate, ((0, 30 * rate),))
    assert map_provider_ranges(manifest, ((first, last),)) == expected


def test_mapping_crosses_a_packed_join_without_including_the_source_gap() -> None:
    manifest = SourceFrameManifest(8000, 220, ((100, 110), (200, 210)))
    assert map_provider_ranges(manifest, ((15, 25),)) == ((108, 110), (200, 202))
    assert map_provider_ranges(manifest, ()) == ()


def test_resampling_padding_cannot_extend_past_original_source_end() -> None:
    manifest = SourceFrameManifest(192000, 101, ((0, 101),))
    assert map_provider_ranges(manifest, ((8, 9),)) == ((96, 101),)
    with pytest.raises(ValueError):
        map_provider_ranges(manifest, ((8, 10),))


def test_sub_source_frame_intervals_disappear_and_adjacent_ranges_do_not_lose_a_frame() -> None:
    manifest = SourceFrameManifest(8000, 20, ((0, 20),))
    assert map_provider_ranges(manifest, ((1, 2),)) == ()
    assert map_provider_ranges(manifest, ((0, 3), (3, 6))) == ((0, 3),)


@pytest.mark.parametrize(
    "ranges",
    [
        ((-1, 2),),
        ((1, 1),),
        ((2, 1),),
        ((0, 21),),
        ((0, 5), (0, 5)),
        ((0, 5), (4, 10)),
        ((10, 12), (0, 5)),
        ((False, 2),),
        ((0, True),),
        ((0, float("nan")),),
        ((0, float("inf")),),
        ((0, 2.0),),
    ],
)
def test_invalid_original_source_ranges_cannot_form_a_manifest(ranges) -> None:
    with pytest.raises(ValueError):
        SourceFrameManifest(8000, 20, ranges)


@pytest.mark.parametrize(
    ("rate", "frames", "ranges"),
    [
        (True, 20, ((0, 2),)),
        (8000.0, 20, ((0, 2),)),
        (7999, 20, ((0, 2),)),
        (8000, False, ((0, 1),)),
        (8000, 0, ((0, 1),)),
        (8000, 8000 * 14400 + 1, ((0, 1),)),
        (8000, 20, ()),
        (8000, 8000 * 61, ((0, 8000 * 61),)),
        (8000, 20, [[0, 2]]),
    ],
)
def test_manifest_rejects_invalid_bounds_and_mutable_or_unbounded_ranges(
    rate, frames, ranges
) -> None:
    with pytest.raises(ValueError):
        SourceFrameManifest(rate, frames, ranges)


@pytest.mark.parametrize(
    "ranges",
    [
        ((-1, 2),),
        ((0, 41),),
        ((0, 5), (0, 5)),
        ((0, 5), (4, 10)),
        ((10, 12), (0, 5)),
        ((False, 2),),
        ((0, True),),
        ((0, float("nan")),),
        ((0, float("inf")),),
        ((0, 2.0),),
        ((1, 1),),
        ((2, 1),),
    ],
)
def test_provider_ranges_reject_untrusted_bounds_without_clamping(ranges) -> None:
    with pytest.raises(ValueError):
        map_provider_ranges(SourceFrameManifest(8000, 20, ((0, 20),)), ranges)
