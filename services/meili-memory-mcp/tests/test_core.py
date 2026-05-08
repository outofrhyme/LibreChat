from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import (
    build_search_filter,
    collect_sender_variants_for_agent,
    extract_headers_from_context,
    normalize_agent_display_name,
    parse_caller_context,
    parse_search_input,
)
from service import MemorySearchService


def test_normalize_agent_display_name():
    assert normalize_agent_display_name("Nolan (5.4)") == "Nolan"
    assert normalize_agent_display_name(" Nolan ") == "Nolan"


def test_collect_sender_variants_for_agent_case_insensitive():
    facets = {"sender": {"Nolan": 10, "Nolan (5.4)": 9, "stacy": 5, "NOLAN helper": 3}}
    assert collect_sender_variants_for_agent(facets, "Nolan") == [
        "Nolan",
        "Nolan (5.4)",
        "NOLAN helper",
    ]


def test_build_search_filter_with_sender_scope_and_conversation():
    value = build_search_filter("user-123", ["Nolan", "Nolan (5.4)"], "Nolan", "conv-1")
    assert "user = 'user-123'" in value
    assert "((sender = 'Nolan' OR sender = 'Nolan (5.4)') OR agent_scope = 'Nolan')" in value
    assert "conversationId = 'conv-1'" in value


def test_parse_search_input_bounds_limit_and_requires_query():
    parsed = parse_search_input(" hi ", 9999, " conv ")
    assert parsed.query == "hi"
    assert parsed.limit >= 1
    assert parsed.conversation_id == "conv"


def test_parse_caller_context_accepts_user_id_alias():
    caller = parse_caller_context({"x-user-id": "user-abc", "x-librechat-agent-name": "Nolan"})
    assert caller.user_id == "user-abc"
    assert caller.agent_display_name == "Nolan"


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


class FakeIndex:
    def __init__(self, hits):
        self._hits = hits
        self.search_calls = []

    def search(self, query, options):
        self.search_calls.append((query, options))
        if options.get("facets") == ["sender"]:
            return {"facetDistribution": {"sender": {"Nolan (5.4)": 1}}}
        return {"hits": self._hits}


class FakeClient:
    def __init__(self, index):
        self._index = index

    def index(self, _name):
        return self._index


def test_search_memory_extracts_text_from_content_when_text_empty():
    index = FakeIndex(
        [
            {
                "messageId": "m2",
                "conversationId": "c2",
                "sender": "assistant",
                "text": "   ",
                "content": [{"type": "image", "text": "no"}, {"type": "text", "text": "from content"}],
            },
        ],
    )
    service = MemorySearchService(client=FakeClient(index), index_name="messages")
    records = service.search_memory(query="hello", user_id="user-1", agent_display_name=None)
    assert records[0]["text"] == "from content"


def test_search_memory_supports_agent_scope_for_user_messages():
    index = FakeIndex(
        [
            {
                "messageId": "m4",
                "conversationId": "c4",
                "sender": "User",
                "agent_scope": "Nolan",
                "text": "what did I ask before?",
            },
            {
                "messageId": "m5",
                "conversationId": "c5",
                "sender": "Nolan (5.4)",
                "agent_scope": "Nolan",
                "text": "you asked for a summary",
            },
        ],
    )
    service = MemorySearchService(client=FakeClient(index), index_name="messages")
    records = service.search_memory(query="ask", user_id="user-1", agent_display_name="Nolan (5.4)")
    assert records[0]["role"] == "user"
    assert records[1]["role"] == "assistant"
    assert "agent_scope = 'Nolan'" in index.search_calls[-1][1]["filter"]
