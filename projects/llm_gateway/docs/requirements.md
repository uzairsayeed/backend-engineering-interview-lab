# LLM Gateway — Finalized Requirements and Assumptions

## 1. Goal

Build a runnable LLM gateway that exposes one limited OpenAI-compatible
streaming API, translates requests to two fictional HTTP providers, normalizes
their SSE responses, and silently falls back from the primary provider to the
backup for the required upstream failures.

## 2. Functional requirements

### 2.1 Public API

- Expose `POST /v1/chat/completions`.
- Accept `Content-Type: application/json`.
- Support only streaming requests.
- Return successful responses as `Content-Type: text/event-stream`.
- Never expose provider-specific request or response formats to clients.

The request format is:

```json
{
  "model": "general-chat",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Explain containers."
    }
  ],
  "stream": true
}
```

Validation rules:

- `model` is required and must be a non-empty string.
- `messages` is required and must contain at least one message.
- A message role must be `system`, `user`, or `assistant`.
- Message content must be a non-empty string.
- `stream` must be present and set to `true`.
- Unsupported request fields are rejected.
- Invalid requests return FastAPI/Pydantic's `422 Unprocessable Entity`.

The normalized stream format is:

```text
data: {"choices":[{"index":0,"delta":{"content":"Hello"}}]}

data: {"choices":[{"index":0,"delta":{"content":" world"}}]}

data: [DONE]

```

### 2.2 Provider A (primary)

Request:

```text
POST {PROVIDER_A_BASE_URL}/v1/generate
Authorization: Bearer {PROVIDER_A_API_KEY}
Content-Type: application/json
```

```json
{
  "model": "provider-a-model",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ],
  "stream": true
}
```

Provider A supports the same roles as the public API.

Provider A stream:

```text
data: {"type":"content_delta","text":"Hello"}

data: {"type":"content_delta","text":" from Provider A"}

data: {"type":"done"}

```

- `content_delta` events are normalized and emitted immediately.
- A `done` event is normalized to `data: [DONE]`.

### 2.3 Provider B (backup)

Request:

```text
POST {PROVIDER_B_BASE_URL}/chat/stream
X-API-Key: {PROVIDER_B_API_KEY}
Content-Type: application/json
```

```json
{
  "model": "provider-b-model",
  "conversation": [
    {
      "speaker": "human",
      "text": "Hello"
    }
  ],
  "streaming": true
}
```

Role mapping:

- `system` → `system`
- `user` → `human`
- `assistant` → `assistant`

Provider B stream:

```text
event: message
data: {"delta":{"content":"Hello"}}

event: message
data: {"delta":{"content":" from Provider B"}}

event: done
data: {}

```

- `message` events are normalized and emitted immediately.
- A `done` event is normalized to `data: [DONE]`.

### 2.4 Routing and fallback

- Provider A is always attempted first.
- Provider B is the only backup.
- Fall back to Provider B when Provider A returns HTTP `429`, `502`, or
  `503` before client-visible content is emitted.
- Close Provider A's response before calling Provider B.
- Do not expose Provider A's failure when Provider B succeeds.
- Make only one backup attempt.
- Other Provider A HTTP statuses do not trigger fallback.
- If Provider A triggers fallback and Provider B also fails before streaming
  starts, return `503 Service Unavailable`.
- If Provider A fails with a non-fallback status before streaming starts,
  return `502 Bad Gateway`.

### 2.5 Streaming lifecycle and failures

- Parse and normalize upstream SSE incrementally.
- Do not buffer a complete provider response in memory.
- Open the upstream stream and prefetch at most its first valid normalized
  event before returning FastAPI's `StreamingResponse`. This establishes a
  usable provider while preserving the ability to return an HTTP error or
  perform status-based fallback before downstream headers are sent.
- Fallback is mandatory only before the first client-visible content chunk.
- Do not attempt fallback after partial output has reached the client.
- If the selected provider disconnects or fails after partial output, close
  the downstream stream without emitting `[DONE]`.
- A malformed provider event before client-visible output results in
  `502 Bad Gateway`.
- A malformed provider event after output has begun terminates the stream;
  the already-sent HTTP status cannot be changed.

## 3. Non-functional requirements

- Use Python 3.11, FastAPI, Pydantic, and Pytest.
- Keep domain/schema, provider translation, routing/service, and HTTP
  responsibilities separated without unnecessary abstractions.
- Keep the implementation readable and explainable in a code review.
- Provider streams and HTTP responses must be closed on success, fallback,
  failure, and client cancellation.
- Do not log API keys or prompt/message content.
- Provide meaningful automated tests.
- Tests must use mocked or fake upstream responses.
- Tests must not require real credentials or make external API calls.
- Provide a Docker image because deployment is mandatory.
- Deploy the runnable service to the supplied DigitalOcean environment.

## 4. Finalized assumptions

1. Exactly two fictional providers are implemented: Provider A and Provider B.
2. Provider A is the primary and Provider B is the backup; clients cannot
   select a provider.
3. The public contract is the limited OpenAI-compatible schema documented
   above, not the complete OpenAI API.
4. Only `stream=true` is supported; there is no non-streaming execution path.
5. Gateway-facing models map internally to one configured model per provider.
6. Provider base URLs, API keys, and provider-specific model names are supplied
   through environment variables.
7. Provider events may be buffered only as needed to parse an individual SSE
   event or establish the upstream response, never to accumulate the full
   completion.
8. Successful completion is represented by exactly one downstream
   `data: [DONE]` event.
9. Mandatory fallback triggers are limited to Provider A HTTP `429`, `502`,
   and `503`.
10. Connection failures and timeouts are optional enhancements and are not
    part of the minimum mandatory fallback behavior.
11. Midstream fallback is unsupported because a second provider could duplicate
    or contradict content already sent by the first.
12. No database is required because no persistent business data is specified.
13. Provider configuration is loaded at application startup; dynamic provider
    or model administration is out of scope.
14. Upstream failures are exposed only as sanitized gateway errors, without
    leaking provider credentials or provider-specific response bodies.

## 5. Out of scope

- Non-streaming chat completions
- More than two providers
- Dynamic routing or provider selection
- Midstream fallback after client-visible output
- Database, SQLAlchemy, SQLite, and Alembic
- Authentication and authorization
- Caching, queues, and rate limiting
- Retry loops, circuit breakers, and distributed infrastructure
- Tool calls, structured output, and multimodal messages
- Real-provider integration tests

## 6. Required automated test coverage

At minimum, tests must cover:

1. Public request validation.
2. Provider A request and role translation.
3. Provider B request and role translation.
4. Provider A SSE normalization.
5. Provider B SSE normalization.
6. Successful streaming through Provider A.
7. Fallback for Provider A HTTP `429`, `502`, and `503`.
8. No fallback for other Provider A HTTP statuses.
9. Provider B success without leaking Provider A's failure.
10. Both providers failing before streaming begins.
11. Malformed upstream events.
12. Upstream failure after partial output.
13. No real external HTTP calls during tests.

## 7. Delivery constraints

- Total assessment duration: 180 minutes.
- Implementation, automated tests, Docker, and deployment: 150 minutes.
- Final review: 30 minutes.
- DigitalOcean access and runtime details will be supplied separately.
