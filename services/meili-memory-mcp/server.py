from __future__ import annotations

from dataclasses import dataclass
import inspect
import os

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.transport_security import TransportSecuritySettings

from core import parse_caller_context, extract_headers_from_context
from service import create_search_service, MemorySearchResult


@dataclass(frozen=True)
class Settings:
    token: str
    public_base_url: str


def _load_settings() -> Settings:
    token = os.getenv("MCP_SHARED_TOKEN", "").strip()
    if not token:
        raise ValueError("MCP_SHARED_TOKEN is required")

    public_base_url = os.getenv("MCP_PUBLIC_BASE_URL", "").strip()
    if not public_base_url:
        raise ValueError("MCP_PUBLIC_BASE_URL is required")

    return Settings(token=token, public_base_url=public_base_url)


SETTINGS = _load_settings()
MEMORY_SEARCH_SERVICE = create_search_service()


class StaticTokenVerifier(TokenVerifier):
    def __init__(self, token: str, scopes: list[str] | None = None) -> None:
        self._token = token
        self._scopes = scopes or ["memory:read"]

    async def verify_token(self, token: str) -> AccessToken | None:
        if token != self._token:
            return None
        return AccessToken(token=token, client_id="shared-token-client", scopes=self._scopes)


mcp = FastMCP(
    "meili-memory-mcp",
    auth=AuthSettings(
        issuer_url=SETTINGS.public_base_url,
        resource_server_url=f"{SETTINGS.public_base_url}/mcp",
        required_scopes=["memory:read"],
    ),
    token_verifier=StaticTokenVerifier(SETTINGS.token),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "rememberwhen-production.up.railway.app",
            "*.up.railway.app",
            ]
        ],
    ),
)


def _apply_runtime_settings(host: str, port: int, path: str) -> None:
    settings = getattr(mcp, "settings", None)
    if settings is None:
        return

    if hasattr(settings, "host"):
        settings.host = host
    if hasattr(settings, "port"):
        settings.port = port
    if hasattr(settings, "path"):
        settings.path = path
    if hasattr(settings, "mount_path"):
        settings.mount_path = path
    if hasattr(settings, "streamable_http_path"):
        settings.streamable_http_path = path


@mcp.tool()
def search_memory(
    query: str | None = None,
    Query: str | None = None,
    limit: int = 8,
    conversationId: str | None = None,
    ctx: Context | None = None,
) -> list[MemorySearchResult]:
    """Search Meilisearch memory by query, always locked to trusted LibreChat user context."""
    headers = extract_headers_from_context(ctx)
    caller = parse_caller_context(headers)
    effective_query = query if isinstance(query, str) and query.strip() else Query
    return MEMORY_SEARCH_SERVICE.search_memory(
        query=effective_query or "",
        user_id=caller.user_id,
        agent_display_name=caller.agent_display_name,
        limit=limit,
        conversation_id=conversationId,
    )


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")

    _apply_runtime_settings(host=host, port=port, path=path)

    run_parameters = inspect.signature(mcp.run).parameters
    run_kwargs: dict[str, object] = {"transport": transport}

    if "host" in run_parameters:
        run_kwargs["host"] = host
    if "port" in run_parameters:
        run_kwargs["port"] = port
    if "path" in run_parameters:
        run_kwargs["path"] = path

    mcp.run(**run_kwargs)
