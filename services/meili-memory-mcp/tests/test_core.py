from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import (
    normalize_agent_display_name,
    collect_sender_variants_for_agent,
    build_search_filter,
    parse_search_input,
    parse_caller_context,
    extract_headers_from_context,
)
from service import MemorySearchService


def test_normalize_agent_display_name():
    assert normalize_agent_display_name("Nolan (5.4)") == "Nolan"
    assert normalize_agent_display_name("Nolan (Ex)") == "Nolan"
    assert normalize_agent_display_name("Stacy (5.2)") == "Stacy"
    assert normalize_agent_display_name(" Nolan ") == "Nolan"


def test_collect_sender_variants_for_agent_case_insensitive():
    facets = {
        "sender": {
            "Nolan": 10,
            "Nolan (5.4)": 9,
            "stacy": 5,
            "NOLAN helper": 3,
        },
    }
    matches = collect_sender_variants_for_agent(facets, "Nolan")
    assert matches == ["Nolan", "Nolan (5.4)", "NOLAN helper"]


def test_build_search_filter_always_contains_user():
    value = build_search_filter("user-123", [], None)
    assert value == "user = 'user-123'"


def test_build_search_filter_with_sender_and_conversation():
    value = build_search_filter("user-123", ["Nolan", "Nolan (5.4)"], "conv-1")
    assert "user = 'user-123'" in value
    assert "(sender = 'Nolan' OR sender = 'Nolan (5.4)')" in value
    assert "conversationId = 'conv-1'" in value


def test_parse_search_input_bounds_limit_and_requires_query():
    parsed = parse_search_input(" hi ", 9999, " conv ")
    assert parsed.query == "hi"
    assert parsed.limit >= 1
    assert parsed.conversation_id == "conv"


def test_parse_caller_context_accepts_user_id_alias():
    caller = parse_caller_context(
        {"x-user-id": "user-abc", "x-librechat-agent-name": "Nolan (5.4)"},
    )
    assert caller.user_id == "user-abc"
    assert caller.agent_display_name == "Nolan (5.4)"


def test_extract_headers_from_nested_request_context():
    class Request:
        headers = {"X-LibreChat-User-Id": "user-123", "Authorization": "Bearer token"}

    class RequestContext:
        request = Request()

    class Ctx:
        request_context = RequestContext()

    headers = extract_headers_from_context(Ctx())
    assert headers["x-librechat-user-id"] == "user-123"
    assert headers["authorization"] == "Bearer token"


def test_extract_headers_from_asgi_style_scope_mapping():
    scope = {
        "type": "http",
        "method": "POST",
        "headers": [
            (b"x-librechat-user-id", b"user-123"),
            (b"authorization", b"Bearer token"),
        ],
    }

    headers = extract_headers_from_context(scope)
    assert headers["x-librechat-user-id"] == "user-123"
    assert headers["authorization"] == "Bearer token"
    assert "type" not in headers
    assert "method" not in headers


def test_parse_caller_context_after_asgi_header_extraction():
    scope = {
        "headers": [
            (b"x-librechat-user-id", b"user-123"),
            (b"x-librechat-agent-name", b""),
        ],
    }
    headers = extract_headers_from_context(scope)
    caller = parse_caller_context(headers)
    assert caller.user_id == "user-123"
    assert caller.agent_display_name is None


class FakeIndex:
    def __init__(self, hits):
        self._hits = hits
        self.search_calls = []

    def search(self, query, options):
        self.search_calls.append((query, options))
        if options.get("facets") == ["sender"]:
            return {"facetDistribution": {}}
        return {"hits": self._hits}


class FakeClient:
    def __init__(self, index):
        self._index = index

    def index(self, _name):
        return self._index


def test_search_memory_uses_non_empty_text_field():
    index = FakeIndex(
        [
            {
                "messageId": "m1",
                "conversationId": "c1",
                "sender": "assistant",
                "text": "hello from text",
                "content": [{"type": "text", "text": "ignored content text"}],
            },
        ],
    )
    service = MemorySearchService(client=FakeClient(index), index_name="messages")

    records = service.search_memory(query="hello", user_id="user-1", agent_display_name=None)

    assert records == [
        {
            "messageId": "m1",
            "conversationId": "c1",
            "sender": "assistant",
            "text": "hello from text",
        },
    ]
    assert index.search_calls[-1][1]["attributesToRetrieve"] == [
        "messageId",
        "conversationId",
        "sender",
        "text",
        "content",
    ]


def test_search_memory_extracts_text_from_content_when_text_empty():
    index = FakeIndex(
        [
            {
                "messageId": "m2",
                "conversationId": "c2",
                "sender": "assistant",
                "text": "   ",
                "content": [
                    {"type": "image", "text": "no"},
                    {"type": "text", "text": "from content"},
                ],
            },
        ],
    )
    service = MemorySearchService(client=FakeClient(index), index_name="messages")

    records = service.search_memory(query="hello", user_id="user-1", agent_display_name=None)

    assert records[0]["text"] == "from content"


def test_search_memory_returns_empty_text_when_text_and_content_missing():
    index = FakeIndex(
        [
            {
                "messageId": "m3",
                "conversationId": "c3",
                "sender": "assistant",
            },
        ],
    )
    service = MemorySearchService(client=FakeClient(index), index_name="messages")

    records = service.search_memory(query="hello", user_id="user-1", agent_display_name=None)

    assert records[0]["text"] == ""
