from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import (
    normalize_agent_display_name,
    collect_sender_variants_for_agent,
    build_search_filter,
    parse_search_input,
)


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
