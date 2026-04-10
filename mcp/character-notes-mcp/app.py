from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import TypedDict

from mcp.server.fastmcp import FastMCP


TEXT_EXTENSIONS = frozenset({".md", ".txt"})
MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "250"))
MAX_LIMIT = int(os.getenv("MAX_LIMIT", "20"))
MAX_SNIPPET_LENGTH = int(os.getenv("MAX_SNIPPET_LENGTH", "400"))
MAX_READ_BYTES = int(os.getenv("MAX_READ_BYTES", str(350_000)))


@dataclass(frozen=True)
class Settings:
    notes_dir: Path
    token: str | None


class SearchResult(TypedDict):
    path: str
    snippet: str
    score: int
    modified_at: str
    size_bytes: int


def _require_notes_dir() -> Path:
    raw_value = os.getenv("NOTES_DIR", "").strip()
    if not raw_value:
        raise ValueError("NOTES_DIR is required")

    notes_path = Path(raw_value).expanduser().resolve()
    if not notes_path.exists():
        raise ValueError(f"NOTES_DIR does not exist: {notes_path}")
    if not notes_path.is_dir():
        raise ValueError(f"NOTES_DIR must be a directory: {notes_path}")

    return notes_path


def _load_settings() -> Settings:
    return Settings(
        notes_dir=_require_notes_dir(),
        token=os.getenv("MCP_SHARED_TOKEN", "").strip() or None,
    )


SETTINGS = _load_settings()
mcp = FastMCP("character-notes-mcp")


def _validate_token(token: str | None) -> None:
    if SETTINGS.token is None:
        return
    if token != SETTINGS.token:
        raise ValueError("Invalid token")


def _to_relative_path(path: Path) -> str:
    return path.relative_to(SETTINGS.notes_dir).as_posix()


def _is_allowed_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS and path.is_file()


def _iter_note_paths() -> list[Path]:
    return [path for path in SETTINGS.notes_dir.rglob("*") if _is_allowed_text_file(path)]


def _safe_note_path(path: str) -> Path:
    requested = (SETTINGS.notes_dir / path).resolve()
    if not requested.is_file():
        raise ValueError("File does not exist")

    try:
        requested.relative_to(SETTINGS.notes_dir)
    except ValueError as error:
        raise ValueError("Path traversal attempt blocked") from error

    if requested.suffix.lower() not in TEXT_EXTENSIONS:
        raise ValueError("Only .md and .txt files are supported")

    return requested


def _read_text_file(path: Path) -> str:
    if path.stat().st_size > MAX_READ_BYTES:
        raise ValueError(f"File exceeds MAX_READ_BYTES ({MAX_READ_BYTES})")

    raw_bytes = path.read_bytes()
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("utf-8", errors="ignore")


def _normalize_query(query: str) -> str:
    normalized = query.strip()
    if not normalized:
        raise ValueError("query is required")

    if len(normalized) > MAX_QUERY_LENGTH:
        raise ValueError(f"query length exceeds MAX_QUERY_LENGTH ({MAX_QUERY_LENGTH})")

    return normalized


def _build_snippet(content: str, query: str) -> str:
    haystack = content.lower()
    needle = query.lower()
    center = haystack.find(needle)
    if center == -1:
        compact = " ".join(content.split())
        return compact[:MAX_SNIPPET_LENGTH]

    start = max(center - (MAX_SNIPPET_LENGTH // 2), 0)
    end = min(start + MAX_SNIPPET_LENGTH, len(content))
    snippet = content[start:end]
    return " ".join(snippet.split())


def _score_match(content: str, query: str) -> int:
    lowered_content = content.lower()
    lowered_query = query.lower()

    phrase_hits = lowered_content.count(lowered_query)
    token_hits = sum(lowered_content.count(token) for token in lowered_query.split())
    return (phrase_hits * 5) + token_hits


def _build_metadata(path: Path) -> tuple[str, int]:
    stat = path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return modified_at, stat.st_size


@mcp.tool()
def search_notes(query: str, limit: int = 8, token: str | None = None) -> list[SearchResult]:
    """Search markdown/text notes and return concise ranked matches."""
    _validate_token(token)
    cleaned_query = _normalize_query(query)
    bounded_limit = max(1, min(limit, MAX_LIMIT))

    results: list[SearchResult] = []

    for path in _iter_note_paths():
        content = _read_text_file(path)
        score = _score_match(content, cleaned_query)
        if score <= 0:
            continue

        modified_at, size_bytes = _build_metadata(path)
        results.append(
            {
                "path": _to_relative_path(path),
                "snippet": _build_snippet(content, cleaned_query),
                "score": score,
                "modified_at": modified_at,
                "size_bytes": size_bytes,
            },
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:bounded_limit]


@mcp.tool()
def read_note(path: str, token: str | None = None) -> str:
    """Return full note contents for a relative path under NOTES_DIR."""
    _validate_token(token)
    safe_path = _safe_note_path(path)
    return _read_text_file(safe_path)


@mcp.tool()
def list_notes(prefix: str = "", token: str | None = None) -> list[str]:
    """List available note files relative to NOTES_DIR."""
    _validate_token(token)
    normalized_prefix = prefix.strip().lower()

    if not normalized_prefix:
        return sorted(_to_relative_path(path) for path in _iter_note_paths())

    return sorted(
        _to_relative_path(path)
        for path in _iter_note_paths()
        if _to_relative_path(path).lower().startswith(normalized_prefix)
    )


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")
    mcp.run(transport=transport, host=host, port=port, path=path)
