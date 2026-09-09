"""Separate trusted-local and workspace-blind MCP surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import ConfigDict, Field

from kt_scaffold import __version__
from kt_scaffold.knowledge import (
    governance_artifacts_get_operation,
    governance_catalog_operation,
    governance_update_check_operation,
    project_blueprint_operation,
    reconciliation_validate_operation,
)
from kt_scaffold.local_creation import project_create_operation, validate_local_workspace_root
from kt_scaffold.models import (
    AgentClientId,
    Answers,
    ArtifactAuthority,
    ArtifactKind,
    GovernanceUpdateProposal,
    ProjectMetadata,
    ReconciliationDecision,
    RuleScope,
)

GOVERNANCE_TOOL_ALIASES = {
    "project_blueprint": "proje_plani",
    "governance_catalog": "yonetisim_katalogu",
    "governance_artifacts_get": "yonetisim_ogelerini_getir",
    "governance_update_check": "yonetisim_guncellemelerini_kontrol_et",
    "reconciliation_validate": "uyumlastirmayi_dogrula",
}
LOCAL_TOOL_ALIASES = {"project_create": "proje_olustur", **GOVERNANCE_TOOL_ALIASES}
LOCAL_PROMPT_ALIASES = {"project_start": "proje_baslat"}

LOCAL_CREATE_ANNOTATIONS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def _answers(
    *,
    project_intent: str,
    primary_domain: str,
    product_name: str,
    product_slug: str,
    env_prefix: str | None,
    api_prefix: str | None,
    tenant_header: str,
    locales: list[str] | None,
    observability: bool,
    agent_clients: list[AgentClientId] | None,
) -> Answers:
    payload: dict[str, object] = {
        "project_intent": project_intent,
        "primary_domain": primary_domain,
        "product_name": product_name,
        "product_slug": product_slug,
        "tenant_header": tenant_header,
        "locales": locales if locales is not None else ["en", "tr"],
        "observability": observability,
    }
    if env_prefix is not None and env_prefix.strip():
        payload["env_prefix"] = env_prefix.strip()
    if api_prefix is not None and api_prefix.strip():
        payload["api_prefix"] = api_prefix.strip()
    if agent_clients is not None:
        payload["agent_clients"] = agent_clients
    return Answers.model_validate(payload)


def _project_blueprint(
    project_intent: str,
    primary_domain: str,
    product_name: str = "Vibe Coding Boilerplate",
    product_slug: str = "app",
    env_prefix: str | None = None,
    api_prefix: str | None = None,
    tenant_header: str = "x-tenant-id",
    locales: list[str] | None = None,
    observability: bool = True,
) -> dict[str, object]:
    return project_blueprint_operation(
        project_intent=project_intent,
        primary_domain=primary_domain,
        product_name=product_name,
        product_slug=product_slug,
        env_prefix=env_prefix,
        api_prefix=api_prefix,
        tenant_header=tenant_header,
        locales=locales if locales is not None else ["en", "tr"],
        observability=observability,
    )


def _governance_catalog(
    kind: ArtifactKind | None = None,
    authority: ArtifactAuthority | None = None,
    scope: RuleScope | None = None,
) -> dict[str, object]:
    return governance_catalog_operation(kind=kind, authority=authority, scope=scope)


def _governance_artifacts_get(ids: list[str]) -> dict[str, object]:
    return governance_artifacts_get_operation(ids)


def _governance_update_check(metadata: ProjectMetadata) -> dict[str, object]:
    return governance_update_check_operation(metadata)


def _reconciliation_validate(
    proposal: GovernanceUpdateProposal,
    decisions: list[ReconciliationDecision],
) -> dict[str, object]:
    return reconciliation_validate_operation(proposal, decisions)


def _register_governance_tools(server: MCPServer[None]) -> None:
    pairs = [
        (
            "project_blueprint",
            "proje_plani",
            _project_blueprint,
            "Return bounded architecture metadata; never access a workspace.",
            "Sınırlı mimari üst verisini döndür; hiçbir workspace'e erişme.",
        ),
        (
            "governance_catalog",
            "yonetisim_katalogu",
            _governance_catalog,
            "List canonical governance artifact metadata.",
            "Kanonik yönetişim öğelerinin üst verisini listele.",
        ),
        (
            "governance_artifacts_get",
            "yonetisim_ogelerini_getir",
            _governance_artifacts_get,
            "Fetch only explicitly selected governance bodies.",
            "Yalnızca açıkça seçilen yönetişim gövdelerini getir.",
        ),
        (
            "governance_update_check",
            "yonetisim_guncellemelerini_kontrol_et",
            _governance_update_check,
            "Compare bounded project metadata with the governance catalog.",
            "Sınırlı proje üst verisini yönetişim kataloğuyla karşılaştır.",
        ),
        (
            "reconciliation_validate",
            "uyumlastirmayi_dogrula",
            _reconciliation_validate,
            "Validate authority-aware local reconciliation decisions.",
            "Yetki sınıflı yerel uyumlaştırma kararlarını doğrula.",
        ),
    ]
    for english, turkish, function, english_description, turkish_description in pairs:
        registered = cast(Any, function)
        server.tool(name=english, description=english_description)(registered)
        server.tool(name=turkish, description=turkish_description)(registered)


def _strict_arguments(server: MCPServer[None]) -> None:
    for tool in server._tool_manager.list_tools():  # noqa: SLF001 -- SDK has no public hook
        model = tool.fn_metadata.arg_model
        model.model_config = ConfigDict(**model.model_config, extra="forbid")
        model.model_rebuild(force=True)
        tool.parameters = model.model_json_schema(by_alias=True)


def build_governance_server() -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(
        "kt-governance",
        version=__version__,
        log_level="WARNING",
        instructions=(
            "Workspace-independent governance and blueprint plane. It never reads, writes, "
            "downloads into, validates or executes a caller workspace."
        ),
    )
    _register_governance_tools(server)
    _strict_arguments(server)
    return server


def _start_prompt(*, language: Literal["en", "tr"], project_goal: str) -> str:
    goal = (
        json.dumps(project_goal.strip(), ensure_ascii=False)
        if project_goal.strip()
        else "(not supplied)"
    )
    if language == "tr":
        return "\n".join(
            [
                "Trusted local KT proje oluşturma aracısını kullanıyorsun.",
                f"Kullanıcının başlangıç hedefi: {goal}",
                (
                    "Hedef eksikse yalnızca 'Oluşturmak istediğiniz ürünün temel amacı nedir?' "
                    "diye sor."
                ),
                (
                    "Amaç yanıtından sonra yalnızca 'Birincil alanı `<primary_domain>` olarak "
                    "belirlememi onaylıyor musunuz?' diye sor."
                ),
                "Ürün adı güvenle türetilemiyorsa yalnızca 'Ürün adı ne olmalı?' diye sor.",
                "Teknoloji, hedef dizin, URL, komut, bundle, applicator veya gizli bilgi sorma.",
                "Küçük harfli ASCII kebab-case domain ve slug türet; prefix alanlarını gönderme.",
                (
                    "Hedef VS Code veya GitHub Copilot'ı açıkça belirtiyorsa agent_clients "
                    'alanını ["github-copilot-vscode"] yap; aksi halde alanı gönderme.'
                ),
                "x-tenant-id, tr/en locale'leri ve observability=true kullan.",
                "Bir kısa özet göster ve yalnızca bir kez açık onay iste.",
                (
                    "Onaydan sonraki yanıtında doğal dil yazmadan yalnızca proje_olustur "
                    "aracını çağır."
                ),
                (
                    "Araç yerel, önceden yüklenmiş generator'ı sabit workspace sınırında "
                    "doğrudan çalıştırır."
                ),
                "Yalnızca receipt durumunu, dosya/entry sayılarını ve tree digest'i raporla.",
            ]
        )
    return "\n".join(
        [
            "Use the trusted local KT project creation tool.",
            f"The user's initial project goal is: {goal}",
            (
                "If purpose is missing, ask only 'What is the primary purpose of the product "
                "you want to create?'."
            ),
            (
                "After the purpose answer ask only 'Do you confirm `<primary_domain>` as the "
                "primary domain?'."
            ),
            "Only when a product name cannot be derived ask 'What should the product be named?'.",
            (
                "Never ask about technology, target paths, URLs, commands, bundles, "
                "applicators or secrets."
            ),
            "Derive lowercase ASCII kebab-case domain and slug; omit both prefix fields.",
            (
                "When the goal explicitly names VS Code or GitHub Copilot, set agent_clients "
                'to ["github-copilot-vscode"]; otherwise omit agent_clients.'
            ),
            "Use x-tenant-id, en/tr locales and observability=true.",
            "Show one compact summary and request exactly one explicit confirmation.",
            "After confirmation write no natural language and call only project_create.",
            (
                "The tool directly invokes the preinstalled generator inside its fixed "
                "workspace boundary."
            ),
            "Report only receipt status, file/entry counts and the verified tree digest.",
        ]
    )


def build_local_server(workspace_root: str | Path) -> MCPServer[None]:
    root = validate_local_workspace_root(workspace_root)
    server: MCPServer[None] = MCPServer(
        "kt-local",
        version=__version__,
        log_level="WARNING",
        instructions=(
            "Trusted local Project Factory and governance surface. Project creation is bound to "
            "the workspace root fixed at server startup and invokes only the installed generator."
        ),
    )

    def project_create(
        project_intent: str,
        primary_domain: str,
        product_name: str = "Vibe Coding Boilerplate",
        product_slug: str = "app",
        tenant_header: str = "x-tenant-id",
        locales: list[str] | None = None,
        observability: bool = True,
        agent_clients: list[AgentClientId] | None = None,
    ) -> dict[str, object]:
        return project_create_operation(
            root,
            _answers(
                project_intent=project_intent,
                primary_domain=primary_domain,
                product_name=product_name,
                product_slug=product_slug,
                env_prefix=None,
                api_prefix=None,
                tenant_header=tenant_header,
                locales=locales,
                observability=observability,
                agent_clients=agent_clients,
            ),
        )

    server.tool(
        name="project_create",
        description=(
            "Create the complete scaffold in the fixed local workspace; no downloads or shell."
        ),
        annotations=LOCAL_CREATE_ANNOTATIONS,
    )(project_create)
    server.tool(
        name="proje_olustur",
        description="Sabit yerel workspace'te tam iskeleti oluştur; indirme veya shell kullanma.",
        annotations=LOCAL_CREATE_ANNOTATIONS,
    )(project_create)
    _register_governance_tools(server)

    @server.prompt(
        name="project_start",
        title="Start a KT project",
        description="Guide trusted local deterministic project creation.",
    )
    def project_start(project_goal: Annotated[str, Field(max_length=4000)] = "") -> str:
        return _start_prompt(language="en", project_goal=project_goal)

    @server.prompt(
        name="proje_baslat",
        title="KT projesi başlat",
        description="Trusted local deterministik proje oluşturmayı yönlendir.",
    )
    def proje_baslat(project_goal: Annotated[str, Field(max_length=4000)] = "") -> str:
        return _start_prompt(language="tr", project_goal=project_goal)

    _strict_arguments(server)
    return server


__all__ = [
    "GOVERNANCE_TOOL_ALIASES",
    "LOCAL_PROMPT_ALIASES",
    "LOCAL_TOOL_ALIASES",
    "build_governance_server",
    "build_local_server",
]
