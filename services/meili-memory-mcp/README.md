# meili-memory-mcp

MCP service template for LibreChat memory retrieval backed by Meilisearch.

## Security model

- The privacy boundary is always the trusted LibreChat user header.
- The service never accepts user scope from tool arguments.
- Agent name is only a retrieval narrowing hint, not authorization.

## Environment

- `MCP_SHARED_TOKEN`: static bearer token for MCP auth.
- `MCP_PUBLIC_BASE_URL`: public HTTPS base URL for MCP auth metadata.
- `MEILI_HOST`: Meilisearch URL.
- `MEILI_API_KEY`: Meilisearch API key.
- `MEILI_MESSAGES_INDEX` (optional, default `messages`).

Optional:

- `LIBRECHAT_USER_ID_HEADER` (default `x-librechat-user-id`)
- `LIBRECHAT_AGENT_NAME_HEADER` (default `x-librechat-agent-name`)
- `MAX_QUERY_LENGTH`, `MAX_LIMIT`, `DEFAULT_LIMIT`

## Expected inbound headers

- `X-LibreChat-User-Id`: trusted current user ID.
- `X-LibreChat-Agent-Name`: trusted current agent display name.
- User ID aliases are also accepted: `X-User-Id`, `User-Id`.

## Tool

### `search_memory`

Inputs:

- `query`
- `limit`
- `conversationId`

Behavior:

1. Reads trusted user and agent context from MCP request metadata headers.
2. Searches only documents matching `user`.
3. Narrows by sender variants and `agent_scope` when an agent name is present.
4. Returns `messageId`, `conversationId`, `sender`, `role`, and extracted `text`.

## Run

```bash
python server.py
```

Default transport is `streamable-http` on `0.0.0.0:8080` path `/mcp`.
