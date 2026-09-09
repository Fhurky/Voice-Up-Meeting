"""VS Code GitHub Copilot custom-agent projection."""

from __future__ import annotations

from kt_scaffold.agent_platform.adapters.base import ProjectionAdapter, yaml_frontmatter
from kt_scaffold.agent_platform.models import (
    CanonicalAgentPackage,
    MappedField,
    RenderedProjection,
    SemanticLoss,
)


class VscodeCopilotAdapter(ProjectionAdapter):
    client_id = "github-copilot-vscode"
    adapter_id = "github-copilot-vscode"
    media_type = "text/markdown"
    allowed_fields = frozenset(
        {"name", "description", "target", "tools", "user-invocable", "disable-model-invocation"}
    )

    def relative_path(self, agent_id: str) -> str:
        return f".github/agents/{agent_id}.agent.md"

    def render(self, package: CanonicalAgentPackage) -> RenderedProjection:
        content = yaml_frontmatter(
            (
                ("name", package.agent_id),
                ("description", self.projected_description(package)),
                ("target", "vscode"),
                ("tools", ("read", "search")),
                ("user-invocable", True),
                ("disable-model-invocation", False),
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
                    projected_to=("tools",),
                ),
            ),
            extra_losses=(
                SemanticLoss(
                    code="AP_LOSS_TOOL_RESOLUTION_UNVERIFIED",
                    canonical="requirements.tools[tool:workspace-read]",
                    disposition="inherited",
                    statement=(
                        "Exact read and search tool resolution requires exact-version runtime "
                        "conformance."
                    ),
                ),
            ),
        )

    def validate(self, content: str, package: CanonicalAgentPackage) -> tuple[str, ...]:
        fields, _ = self.validate_frontmatter(content, package)
        if set(fields) != self.allowed_fields:
            raise ValueError("VS Code projection contains unsupported or missing fields")
        if fields["target"] != "vscode" or fields["tools"] != ["read", "search"]:
            raise ValueError("VS Code projection violates target or tool boundary")
        if "agents" in fields or "model" in fields:
            raise ValueError("VS Code projection must not grant delegation or pin a model")
        return (
            "yaml-frontmatter-parse",
            "stable-field-allowlist",
            "read-search-only",
            "instructions-present",
        )
