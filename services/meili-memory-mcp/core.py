from __future__ import annotations

from dataclasses import dataclass
import os
import re
from collections.abc import Sequence
from typing import Mapping, Any

MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "250"))
MAX_LIMIT = int(os.getenv("MAX_LIMIT", "20"))
DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "8"))
DEBUG_HEADERS = os.getenv("DEBUG_HEADERS", "").strip().lower() in {"1", "true", "yes", "on"}

USER_ID_HEADER = os.getenv("LIBRECHAT_USER_ID_HEADER", "x-librechat-user-id").lower()
AGENT_NAME_HEADER = os.getenv("LIBRECHAT_AGENT_NAME_HEADER", "x-librechat-agent-name").lower()
USER_ID_HEADER_ALIASES = (
    USER_ID_HEADER,
    "x-user-id",
    "user-id",
)


@dataclass(frozen=True)
class CallerContext:
    user_id: str
    agent_display_name: str | None


@dataclass(frozen=True)
class SearchInput:
    query: str
    limit: int
    conversation_id: str | None


def normalize_agent_display_name(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip()
    if not normalized:
        return ""
    return re.sub(r"\s*\([^)]*\)\s*$", "", normalized).strip()


def parse_search_input(query: str, limit: int | None, conversation_id: str | None) -> SearchInput:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("query is required")
    if len(cleaned_query) > MAX_QUERY_LENGTH:
        raise ValueError(f"query length exceeds MAX_QUERY_LENGTH ({MAX_QUERY_LENGTH})")

    safe_limit = DEFAULT_LIMIT if limit is None else limit
    bounded_limit = max(1, min(int(safe_limit), MAX_LIMIT))
    cleaned_conversation = conversation_id.strip() if isinstance(conversation_id, str) else None
    return SearchInput(
        query=cleaned_query,
        limit=bounded_limit,
        conversation_id=cleaned_conversation if cleaned_conversation else None,
    )


def get_required_header(headers: Mapping[str, str], header_name: str) -> str:
    value = headers.get(header_name.lower(), "").strip()
    if not value:
        raise ValueError(f"Missing required trusted header: {header_name}")
    return value


def get_required_header_from_aliases(headers: Mapping[str, str], header_names: tuple[str, ...]) -> str:
    for header_name in header_names:
        value = headers.get(header_name.lower(), "").strip()
        if value:
            return value
    joined = ", ".join(header_names)
    raise ValueError(f"Missing required trusted header (aliases checked): {joined}")


def parse_caller_context(headers: Mapping[str, str]) -> CallerContext:
    if DEBUG_HEADERS:
        safe_headers = {
            k: ("<redacted>" if k == "authorization" else v)
            for k, v in headers.items()
        }
        print("DEBUG headers:", safe_headers, flush=True)

    user_id = get_required_header_from_aliases(headers, USER_ID_HEADER_ALIASES)
    raw_agent_name = headers.get(AGENT_NAME_HEADER, "").strip()
    return CallerContext(user_id=user_id, agent_display_name=raw_agent_name or None)


def extract_headers_from_context(ctx: Any) -> dict[str, str]:
    if ctx is None:
        return {}

    def normalize_headers(headers: Mapping[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in headers.items():
            normalized[str(key).lower()] = str(value)
        return normalized

    def decode_header_part(value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    def normalize_asgi_headers(headers: Sequence[Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for item in headers:
            if not isinstance(item, Sequence) or len(item) != 2:
                continue
            key, value = item
            header_key = decode_header_part(key).lower()
            header_value = decode_header_part(value)
            normalized[header_key] = header_value
        return normalized

    def extract_from_value(value: Any) -> dict[str, str]:
        if value is None:
            return {}

        headers = getattr(value, "headers", None)
        if isinstance(headers, Mapping):
            return normalize_headers(headers)
        if isinstance(headers, Sequence) and not isinstance(headers, (str, bytes, bytearray)):
            normalized = normalize_asgi_headers(headers)
            if normalized:
                return normalized

        meta = getattr(value, "meta", None)
        if meta is not None:
            meta_headers = getattr(meta, "headers", None)
            if isinstance(meta_headers, Mapping):
                return normalize_headers(meta_headers)
            if isinstance(meta_headers, Sequence) and not isinstance(
                meta_headers,
                (str, bytes, bytearray),
            ):
                normalized = normalize_asgi_headers(meta_headers)
                if normalized:
                    return normalized

        if isinstance(value, Mapping) and "headers" in value:
            mapping_headers = value.get("headers")
            if isinstance(mapping_headers, Mapping):
                return normalize_headers(mapping_headers)
            if isinstance(mapping_headers, Sequence) and not isinstance(
                mapping_headers,
                (str, bytes, bytearray),
            ):
                normalized = normalize_asgi_headers(mapping_headers)
                if normalized:
                    return normalized

        return {}

    request_context = getattr(ctx, "request_context", None)
    request = getattr(ctx, "request", None)

    candidates = [
        ctx,
        request_context,
        request,
        getattr(ctx, "fastmcp_context", None),
        getattr(ctx, "meta", None),
        getattr(ctx, "session", None),
        getattr(request_context, "request", None) if request_context is not None else None,
        getattr(request, "request", None) if request is not None else None,
    ]

    for candidate in candidates:
        extracted = extract_from_value(candidate)
        if extracted:
            return extracted

    return {}


def build_user_filter(user_id: str) -> str:
    escaped_user = user_id.replace("'", "\\'")
    return f"user = '{escaped_user}'"


def build_sender_filter(sender_values: list[str]) -> str | None:
    if len(sender_values) == 0:
        return None
    escaped = [sender.replace("'", "\\'") for sender in sender_values]
    fragments = [f"sender = '{sender}'" for sender in escaped]
    return "(" + " OR ".join(fragments) + ")"


def build_agent_scope_filter(agent_scope: str) -> str | None:
    normalized_scope = normalize_agent_display_name(agent_scope)
    if not normalized_scope:
        return None
    escaped_scope = normalized_scope.replace("'", "\\'")
    return f"agent_scope = '{escaped_scope}'"


def build_conversation_filter(conversation_id: str | None) -> str | None:
    if not conversation_id:
        return None
    escaped_conversation = conversation_id.replace("'", "\\'")
    return f"conversationId = '{escaped_conversation}'"


def collect_sender_variants_for_agent(
    facets: Mapping[str, Any] | None,
    normalized_agent_name: str,
) -> list[str]:
    if not facets:
        return []
    if not normalized_agent_name:
        return []

    sender_bucket = facets.get("sender")
    if not isinstance(sender_bucket, Mapping):
        return []

    needle = normalized_agent_name.lower()
    matches: list[str] = []
    for sender_value in sender_bucket.keys():
        candidate = str(sender_value)
        if needle in candidate.lower():
            matches.append(candidate)
    return matches


def build_search_filter(
    user_id: str,
    sender_values: list[str],
    agent_scope: str,
    conversation_id: str | None,
) -> str:
    filters: list[str] = [build_user_filter(user_id)]

    scope_clauses: list[str] = []
    sender_filter = build_sender_filter(sender_values)
    if sender_filter:
        scope_clauses.append(sender_filter)

    agent_scope_filter = build_agent_scope_filter(agent_scope)
    if agent_scope_filter:
        scope_clauses.append(agent_scope_filter)

    if scope_clauses:
        filters.append("(" + " OR ".join(scope_clauses) + ")")

    conversation_filter = build_conversation_filter(conversation_id)
    if conversation_filter:
        filters.append(conversation_filter)

    return " AND ".join(filters)
