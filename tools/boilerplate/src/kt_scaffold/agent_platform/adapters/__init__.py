"""Production custom-agent projection adapters."""

from kt_scaffold.agent_platform.adapters.base import ProjectionAdapter
from kt_scaffold.agent_platform.adapters.claude_code import ClaudeCodeAdapter
from kt_scaffold.agent_platform.adapters.codex import CodexAdapter
from kt_scaffold.agent_platform.adapters.cursor import CursorAdapter
from kt_scaffold.agent_platform.adapters.vscode_copilot import VscodeCopilotAdapter

ADAPTERS: tuple[ProjectionAdapter, ...] = (
    ClaudeCodeAdapter(),
    CodexAdapter(),
    CursorAdapter(),
    VscodeCopilotAdapter(),
)

__all__ = ["ADAPTERS", "ProjectionAdapter"]
