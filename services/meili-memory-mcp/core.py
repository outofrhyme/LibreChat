from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Mapping, Any

MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "250"))
MAX_LIMIT = int(os.getenv("MAX_LIMIT", "20"))
DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "8"))

USER_ID_HEADER = os.getenv("LIBRECHAT_USER_ID_HEADER", "x-librechat-user-id").lower()
AGENT_NAME_HEADER = os.getenv("LIBRECHAT_AGENT_NAME_HEADER", "x-librechat-agent-name").lower()


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


def parse_caller_context(headers: Mapping[str, str]) -> CallerContext:
    user_id = get_required_header(headers, USER_ID_HEADER)
    raw_agent_name = headers.get(AGENT_NAME_HEADER, "").strip()
    return CallerContext(user_id=user_id, agent_display_name=raw_agent_name or None)


def extract_headers_from_context(ctx: Any) -> dict[str, str]:
    request = getattr(ctx, "request_context", None)
    if request is None:
        request = getattr(ctx, "request", None)
    if request is None:
        return {}

    headers = getattr(request, "headers", None)
    if headers is None:
        meta = getattr(request, "meta", None)
        headers = getattr(meta, "headers", None) if meta is not None else None

    if not isinstance(headers, Mapping):
        return {}

    lowered: dict[str, str] = {}
    for key, value in headers.items():
        lowered[str(key).lower()] = str(value)
    return lowered


def build_user_filter(user_id: str) -> str:
    escaped_user = user_id.replace("'", "\\'")
    return f"user = '{escaped_user}'"


def build_sender_filter(sender_values: list[str]) -> str | None:
    if len(sender_values) == 0:
        return None
    escaped = [sender.replace("'", "\\'") for sender in sender_values]
    fragments = [f"sender = '{sender}'" for sender in escaped]
    return "(" + " OR ".join(fragments) + ")"


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


def build_search_filter(user_id: str, sender_values: list[str], conversation_id: str | None) -> str:
    filters: list[str] = [build_user_filter(user_id)]

    sender_filter = build_sender_filter(sender_values)
    if sender_filter:
        filters.append(sender_filter)

    conversation_filter = build_conversation_filter(conversation_id)
    if conversation_filter:
        filters.append(conversation_filter)

    return " AND ".join(filters)
