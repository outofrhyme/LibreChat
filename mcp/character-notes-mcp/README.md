# Character Notes MCP Service

A minimal MCP server for shared note retrieval across cloned LibreChat agents.

## Features

- `search_notes(query, limit=8, token=None)` with ranked snippets
- `read_note(path, token=None)` for full file reads
- `list_notes(prefix="", token=None)` for quick verification
- Supports `.md` and `.txt` files from one canonical notes directory
- Path traversal protection for `read_note`
- Optional shared token auth (`MCP_SHARED_TOKEN`)
- Works as a standalone Railway service

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `NOTES_DIR` | ✅ | — | Absolute path to your notes corpus |
| `MCP_SHARED_TOKEN` | ❌ | empty | Shared token required by all tools if set |
| `MCP_TRANSPORT` | ❌ | `streamable-http` | MCP transport mode |
| `HOST` | ❌ | `0.0.0.0` | Bind host |
| `PORT` | ❌ | `8080` | Bind port |
| `MCP_HTTP_PATH` | ❌ | `/mcp` | MCP HTTP path (used when supported by installed SDK) |
| `MAX_QUERY_LENGTH` | ❌ | `250` | Max allowed query length |
| `MAX_LIMIT` | ❌ | `20` | Max search result count |
| `MAX_SNIPPET_LENGTH` | ❌ | `400` | Snippet length in chars |
| `MAX_READ_BYTES` | ❌ | `350000` | Max full-file read size |

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export NOTES_DIR="$(pwd)/example-notes"
export MCP_SHARED_TOKEN="replace-me"
python app.py
```

Server defaults to `http://localhost:8080/mcp` when the installed MCP SDK accepts host/port/path run arguments.

## Railway Deploy

1. Create a new Railway service from this folder/repo.
2. Add a dedicated volume, for example mounted at `/data/notes`.
3. Set env vars:
   - `NOTES_DIR=/data/notes`
   - `MCP_SHARED_TOKEN=<strong-random-token>`
   - `PORT=8080`
4. Deploy.
5. Populate `/data/notes` with your `.md`/`.txt` files.

## Syncing Notes from GitHub

Use GitHub as source-of-truth and sync note files into the mounted `NOTES_DIR` path. You can do this manually first, then automate later with a deploy/startup script.

## LibreChat MCP Config Example

Add this server in your LibreChat MCP server configuration:

```yaml
mcpServers:
  character_notes:
    type: streamable-http
    url: https://<your-railway-host>/mcp
    timeout: 30000
```

Then pass the shared token in tool arguments (`token`) from your agent instructions for now:

- `search_notes(query="...", limit=8, token="<same-token>")`
- `read_note(path="folder/file.md", token="<same-token>")`

If you prefer header-based auth later, you can add an auth proxy or switch to OAuth/JWT upstream.

## Future Evolution (Semantic Retrieval)

When ready for semantic retrieval:

1. Keep these tools and signatures stable.
2. Add an index layer that writes embeddings for each file chunk.
3. Replace `search_notes` internals with hybrid ranking (keyword + vector similarity).
4. Keep `read_note` unchanged for source-grounded reads.
