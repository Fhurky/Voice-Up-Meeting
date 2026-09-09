"""Typed wrapper around the standard-library-only scaffold applicator."""

from __future__ import annotations

from pathlib import Path

from kt_scaffold.bundle import validate_descriptor_integrity
from kt_scaffold.models import ScaffoldApplicationReceipt, ScaffoldBundleDescriptor
from kt_scaffold.safety import SafetyError
from kt_scaffold.standalone_applicator import ApplicationError, apply_bundle


def apply_scaffold_bundle(
    archive_path: str | Path,
    target_dir: str | Path,
    descriptor: ScaffoldBundleDescriptor,
    *,
    inject_publish_failure: bool = False,
) -> ScaffoldApplicationReceipt:
    """Verify and atomically publish a prepared scaffold into an empty target."""
    try:
        validate_descriptor_integrity(descriptor)
        receipt = apply_bundle(
            archive_path,
            target_dir,
            descriptor.model_dump(mode="json", exclude_none=True),
            expected_bundle_id=descriptor.bundle_id,
            inject_publish_failure=inject_publish_failure,
        )
        return ScaffoldApplicationReceipt.model_validate(receipt)
    except (ApplicationError, ValueError) as exc:
        raise SafetyError(str(exc)) from exc
