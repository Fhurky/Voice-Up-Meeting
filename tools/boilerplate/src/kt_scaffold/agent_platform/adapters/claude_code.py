"""Claude Code project subagent projection."""

from __future__ import annotations

from kt_scaffold.agent_platform.adapters.base import ProjectionAdapter, yaml_frontmatter
from kt_scaffold.agent_platform.models import CanonicalAgentPackage, MappedField, RenderedProjection


class ClaudeCodeAdapter(ProjectionAdapter):
    client_id = "claude-code"
    adapter_id = "claude-code"
    media_type = "text/markdown"
    allowed_fields = frozenset(
        {"name", "description", "tools", "disallowedTools", "model", "permissionMode"}
    )

    def relative_path(self, agent_id: str) -> str:
        return f".claude/agents/{agent_id}.md"

    def render(self, package: CanonicalAgentPackage) -> RenderedProjection:
        content = yaml_frontmatter(
            (
                ("name", package.agent_id),
                ("description", self.projected_description(package)),
                ("tools", "Read, Glob, Grep"),
                ("disallowedTools", "Write, Edit, Bash, Agent"),
                ("model", "inherit"),
                ("permissionMode", "plan"),
            ),
            self.body(package),
        )
        return self.projection(
            package,
            content=content,
            mapped_fields=(
                *self.base_mappings(),
                MappedField(
                    canonical="requirements.tools[tool:workspace-read]",
                    projected_to=("tools", "disallowedTools"),
                ),
                MappedField(canonical="runtime.workspace_access", projected_to=("permissionMode",)),
            ),
        )

    def validate(self, content: str, package: CanonicalAgentPackage) -> tuple[str, ...]:
        fields, _ = self.validate_frontmatter(content, package)
        if set(fields) != self.allowed_fields:
            raise ValueError("Claude projection contains unsupported or missing fields")
        if (
            fields["tools"] != "Read, Glob, Grep"
            or fields["disallowedTools"] != "Write, Edit, Bash, Agent"
        ):
            raise ValueError("Claude projection violates tool boundary")
        if fields["model"] != "inherit" or fields["permissionMode"] != "plan":
            raise ValueError("Claude projection violates inheritance or plan-mode boundary")
        return (
            "yaml-frontmatter-parse",
            "stable-field-allowlist",
            "read-only-tool-boundary",
            "instructions-present",
        )
