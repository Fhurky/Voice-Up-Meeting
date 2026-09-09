"""Deterministic, content-addressed projection lock construction."""

from __future__ import annotations

import hashlib
import json

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from kt_scaffold.agent_platform.models import (
    CanonicalPlatform,
    ContentReference,
    ManifestArtifact,
    ProjectionArtifact,
    ProjectionManifest,
)


def canonical_json(value: object) -> str:
    """Serialize a model dump as stable UTF-8 JSON with no volatile fields."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def build_projection_manifest(
    platform: CanonicalPlatform,
    artifacts: tuple[ProjectionArtifact, ...],
    *,
    compiler_version: str,
) -> ProjectionManifest:
    inputs: dict[str, ContentReference] = {item.path: item for item in platform.platform_inputs}
    for package in platform.agents:
        for item in package.inputs:
            inputs[item.path] = item
    manifest_artifacts = tuple(
        ManifestArtifact(
            client_id=item.client_id,
            agent_id=item.agent_id,
            relative_path=item.relative_path,
            media_type=item.media_type,
            adapter_id=item.adapter_id,
            adapter_version=item.adapter_version,
            client_version_range=item.client_version_range,
            generation_status=item.generation_status,
            candidate_inventory_ref=item.candidate_inventory_ref,
            runtime_admission=item.runtime_admission,
            runtime_conformance=item.runtime_conformance,
            canonical_schema_version=item.canonical_schema_version,
            canonical_contract_version=item.canonical_contract_version,
            documentation_sources=item.documentation_sources,
            omitted_optional_capabilities=item.omitted_optional_capabilities,
            sha256=item.sha256,
            inputs=item.inputs,
            mapped_fields=item.mapped_fields,
            semantic_losses=item.semantic_losses,
            external_controls=item.external_controls,
            validations=item.validations,
        )
        for item in sorted(artifacts, key=lambda artifact: artifact.relative_path)
    )
    manifest = ProjectionManifest(
        compiler_version=compiler_version,
        inputs=tuple(inputs[path] for path in sorted(inputs)),
        artifacts=manifest_artifacts,
    )
    schema = ProjectionManifest.model_json_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest.model_dump(mode="json"))
    return manifest


def serialize_projection_manifest(manifest: ProjectionManifest) -> tuple[str, str]:
    content = canonical_json(manifest.model_dump(mode="json"))
    return content, hashlib.sha256(content.encode("utf-8")).hexdigest()


__all__ = ["build_projection_manifest", "canonical_json", "serialize_projection_manifest"]
