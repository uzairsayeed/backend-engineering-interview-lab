# LLM Gateway API Contract

## Purpose

The public API gives clients one streaming chat-completion contract while the
gateway handles provider-specific authentication, request translation, SSE
normalization, and pre-stream fallback internally.

The API intentionally implements only the subset required by this assessment.
It is OpenAI-compatible in shape, but it is not a complete implementation of
the OpenAI API.

## Endpoints

### Health

```text
GET /health
```

Purpose:

- Provide a lightweight process-health check for deployment platforms.
- Avoid calling Provider A or Provider B.

Success:

```text
200 OK
Content-Type: application/json
```

```json
{
  "status": "ok"
}
```

### Chat completion

```text
POST /v1/chat/completions
Content-Type: application/json
```

There is no non-streaming variant.

## Request object

### ChatCompletionRequest

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

Fields:

- `model`: required, non-empty string. This is the gateway-facing model name.
- `messages`: required, non-empty array of `ChatMessage` objects.
- `stream`: required and must be the boolean value `true`.

Unknown fields are rejected.

### ChatMessage

```json
{
  "role": "user",
  "content": "Hello"
}
```

Fields:

- `role`: required enum with values `system`, `user`, or `assistant`.
- `content`: required, non-empty string.

## Successful response

Status:

```text
200 OK
```

Headers:

```text
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

Each SSE event is separated by a blank line.

### ContentDeltaChunk

```text
data: {"choices":[{"index":0,"delta":{"content":"Hello"}}]}

```

The JSON payload has this shape:

```json
{
  "choices": [
    {
      "index": 0,
      "delta": {
        "content": "Hello"
      }
    }
  ]
}
```

Fields:

- `choices`: an array containing one streamed choice.
- `choices[0].index`: always `0` in this limited contract.
- `choices[0].delta.content`: the next client-visible text fragment.

Provider identifiers, provider event names, and provider-specific payloads are
never included.

### Completion event

A successful stream ends with exactly:

```text
data: [DONE]

```

`[DONE]` is emitted only after the selected provider reports successful
completion. It is not emitted after a malformed event, disconnect, or other
midstream failure.

### Complete example

```text
data: {"choices":[{"index":0,"delta":{"content":"Containers"}}]}

data: {"choices":[{"index":0,"delta":{"content":" isolate applications."}}]}

data: [DONE]

```

## Errors before streaming starts

Before returning the SSE response, the gateway opens the selected upstream
stream and prefetches at most its first valid normalized event. This allows
pre-stream failures to be returned as normal HTTP errors.

Gateway-generated errors use this shape:

```json
{
  "error": {
    "code": "upstream_error",
    "message": "The upstream provider could not process the request."
  }
}
```

`error.code` is a stable, machine-readable gateway code. `error.message` is a
sanitized human-readable summary. Validation errors additionally include a
`details` array.

Provider response bodies, API keys, and sensitive configuration are never
included in error responses.

### 422 Unprocessable Entity — `validation_error`

Returned when the request does not satisfy the public schema, including:

- Missing or blank `model`
- Empty or missing `messages`
- Unsupported message role
- Empty message content
- Missing `stream`
- `stream` set to `false`
- Unknown request or message fields

The gateway normalizes FastAPI/Pydantic validation failures into:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [
      {
        "loc": ["body", "stream"],
        "msg": "Input should be True",
        "type": "literal_error"
      }
    ]
  }
}
```

### 502 Bad Gateway — `upstream_error`

Returned when Provider A fails before streaming with an HTTP status that does
not trigger fallback.

```json
{
  "error": {
    "code": "upstream_error",
    "message": "The upstream provider could not process the request."
  }
}
```

### 502 Bad Gateway — `invalid_upstream_response`

Returned when the selected provider returns malformed or unsupported SSE data
before any downstream headers or content have been emitted.

```json
{
  "error": {
    "code": "invalid_upstream_response",
    "message": "The upstream provider returned an invalid response."
  }
}
```

### 503 Service Unavailable — `all_providers_failed`

Returned when Provider A returns `429`, `502`, or `503`, fallback is attempted,
and Provider B also fails before downstream streaming starts.

```json
{
  "error": {
    "code": "all_providers_failed",
    "message": "No provider is currently available."
  }
}
```

### 500 Internal Server Error — `internal_error`

Returned for an unexpected gateway failure before streaming starts.

```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected gateway error occurred."
  }
}
```

## Errors after streaming starts

After the `200 OK` headers have been sent, the gateway cannot change the HTTP
status or return a JSON error object.

If the selected provider disconnects, sends malformed data, or otherwise fails
after client-visible content:

1. No fallback is attempted.
2. No provider-specific error is emitted.
3. `[DONE]` is not emitted.
4. The downstream stream is closed cleanly.

Clients can distinguish successful completion from an interrupted stream by
whether they received `[DONE]`.

## Fallback behavior visible through the API

Fallback is transparent:

1. Provider A is attempted first.
2. Provider A HTTP `429`, `502`, or `503` triggers Provider B before output.
3. If Provider B succeeds, the client receives `200 OK` and only Provider B's
   normalized events.
4. Provider A's status and response body are not exposed.
5. Only one Provider B attempt is made.

Connection failures and timeouts are not mandatory fallback triggers in the
minimum scope.
