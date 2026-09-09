"""Cursor project subagent projection."""

from __future__ import annotations

from kt_scaffold.agent_platform.adapters.base import ProjectionAdapter, yaml_frontmatter
from kt_scaffold.agent_platform.models import (
    CanonicalAgentPackage,
    MappedField,
    RenderedProjection,
    SemanticLoss,
)


class CursorAdapter(ProjectionAdapter):
    client_id = "cursor"
    adapter_id = "cursor"
    media_type = "text/markdown"
    allowed_fields = frozenset({"name", "description", "model", "readonly", "is_background"})

    def relative_path(self, agent_id: str) -> str:
        return f".cursor/agents/{agent_id}.md"

    def render(self, package: CanonicalAgentPackage) -> RenderedProjection:
        content = yaml_frontmatter(
            (
                ("name", package.agent_id),
                ("description", self.projected_description(package)),
                ("model", "inherit"),
                ("readonly", True),
                ("is_background", False),
            ),
            self.body(package),
        )
        return self.projection(
            package,
            content=content,
            mapped_fields=(
                *self.base_mappings(),
                MappedField(canonical="runtime.workspace_access", projected_to=("readonly",)),
            ),
            extra_losses=(
                SemanticLoss(
                    code="AP_LOSS_CURSOR_POLICY_EXTERNAL",
                    canonical="permissions",
                    disposition="external-control",
                    statement=(
                        "Cursor IDE and CLI permission surfaces require separate "
                        "effective-runtime validation."
                    ),
                ),
            ),
        )

    def validate(self, content: str, package: CanonicalAgentPackage) -> tuple[str, ...]:
        fields, _ = self.validate_frontmatter(content, package)
        if set(fields) != self.allowed_fields:
            raise ValueError("Cursor projection contains unsupported or missing fields")
        if fields["model"] != "inherit" or fields["readonly"] is not True:
            raise ValueError("Cursor projection violates inheritance or read-only boundary")
        if fields["is_background"] is not False:
            raise ValueError("Cursor projection unexpectedly enables background execution")
        return (
            "yaml-frontmatter-parse",
            "stable-field-allowlist",
            "read-only",
            "instructions-present",
        )
