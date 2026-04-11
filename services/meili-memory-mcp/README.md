# meili-memory-mcp

MCP service template (FastMCP + shared token auth) for LibreChat memory retrieval backed by Meilisearch.

## Security model

- **Privacy boundary is always `user`**.
- The service only reads user scope from trusted MCP request metadata headers (set by LibreChat), never from tool arguments.
- `agent name` is used only for retrieval scoping (sender-family narrowing), not authorization.

## Required environment variables

- `MCP_SHARED_TOKEN`: static bearer token for MCP auth.
- `MCP_PUBLIC_BASE_URL`: public HTTPS base URL for MCP auth metadata.
- `MEILI_HOST`: Meilisearch URL.
- `MEILI_API_KEY`: Meilisearch API key.
- `MEILI_MESSAGES_INDEX` (optional, default `messages`).

Optional:

- `LIBRECHAT_USER_ID_HEADER` (default `x-librechat-user-id`)
- `LIBRECHAT_AGENT_NAME_HEADER` (default `x-librechat-agent-name`)
- `MAX_QUERY_LENGTH`, `MAX_LIMIT`, `DEFAULT_LIMIT`

## Expected inbound headers from LibreChat

- `X-LibreChat-User-Id`: trusted current user ID (required).
- `X-LibreChat-Agent-Name`: trusted current agent display name (optional).

## Tool

### `search_memory`

Inputs:
- `query` (string, required)
- `Query` (string, optional alias for clients that capitalize tool args)
- `limit` (integer, optional)
- `conversationId` (string, optional)

Behavior:
1. Build facet query: `q: ""`, filter `user = '<trusted-user-id>'`, `facets: ["sender"]`, `limit: 0`.
2. Normalize agent display name by stripping one trailing parenthetical (`Nolan (5.4)` -> `Nolan`).
3. Dynamically match sender facet keys containing normalized agent name (case-insensitive).
4. Execute real Meili search on `text` with filter:
   - always `user = '<trusted-user-id>'`
   - optional sender OR-list using exact sender strings from facet discovery
   - optional `conversationId`
5. Return only `messageId`, `conversationId`, `sender`, `text`.

## Run

```bash
python server.py
```

Default transport is `streamable-http` on `0.0.0.0:8080` path `/mcp`.
