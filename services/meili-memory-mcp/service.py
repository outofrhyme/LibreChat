from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, TypedDict

from meilisearch import Client

from .core import (
    parse_search_input,
    normalize_agent_display_name,
    collect_sender_variants_for_agent,
    build_search_filter,
)


class MemorySearchResult(TypedDict):
    messageId: str
    conversationId: str
    sender: str
    text: str


@dataclass(frozen=True)
class MeiliSettings:
    host: str
    api_key: str
    index_name: str


def load_meili_settings() -> MeiliSettings:
    host = os.getenv("MEILI_HOST", "").strip()
    api_key = os.getenv("MEILI_API_KEY", "").strip()
    index_name = os.getenv("MEILI_MESSAGES_INDEX", "messages").strip()

    if not host:
        raise ValueError("MEILI_HOST is required")
    if not api_key:
        raise ValueError("MEILI_API_KEY is required")
    if not index_name:
        raise ValueError("MEILI_MESSAGES_INDEX is required")

    return MeiliSettings(host=host, api_key=api_key, index_name=index_name)


class MemorySearchService:
    def __init__(self, client: Client, index_name: str) -> None:
        self._client = client
        self._index_name = index_name

    def _index(self):
        return self._client.index(self._index_name)

    def _discover_sender_variants(self, user_id: str, normalized_agent_name: str) -> list[str]:
        if not normalized_agent_name:
            return []

        facet_result = self._index().search(
            "",
            {
                "filter": build_search_filter(user_id, [], None),
                "facets": ["sender"],
                "limit": 0,
            },
        )
        facets = facet_result.get("facetDistribution")
        return collect_sender_variants_for_agent(facets, normalized_agent_name)

    def search_memory(
        self,
        query: str,
        user_id: str,
        agent_display_name: str | None,
        limit: int | None = None,
        conversation_id: str | None = None,
    ) -> list[MemorySearchResult]:
        parsed = parse_search_input(query=query, limit=limit, conversation_id=conversation_id)

        normalized_agent_name = normalize_agent_display_name(agent_display_name)
        sender_variants = self._discover_sender_variants(user_id, normalized_agent_name)

        filters = build_search_filter(
            user_id=user_id,
            sender_values=sender_variants,
            conversation_id=parsed.conversation_id,
        )

        result = self._index().search(
            parsed.query,
            {
                "filter": filters,
                "limit": parsed.limit,
                "attributesToRetrieve": ["messageId", "conversationId", "sender", "text"],
            },
        )

        hits = result.get("hits")
        if not isinstance(hits, list):
            return []

        records: list[MemorySearchResult] = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            records.append(
                {
                    "messageId": str(hit.get("messageId", "")),
                    "conversationId": str(hit.get("conversationId", "")),
                    "sender": str(hit.get("sender", "")),
                    "text": str(hit.get("text", "")),
                },
            )
        return records


def create_search_service() -> MemorySearchService:
    settings = load_meili_settings()
    client = Client(settings.host, settings.api_key)
    return MemorySearchService(client=client, index_name=settings.index_name)
