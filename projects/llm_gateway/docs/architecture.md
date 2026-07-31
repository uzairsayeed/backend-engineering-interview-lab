# LLM Gateway Architecture and Control Flow

## Purpose

The system hides two different provider APIs behind one streaming contract.
It translates requests, selects the primary or backup provider, incrementally
normalizes SSE events, and guarantees status-based fallback before any
client-visible content is sent.

The design is intentionally small: one HTTP application, one routing service,
and two provider adapters. There is no persistence layer because the gateway
stores no business data.

## System context

```text
                         HTTPS/SSE
┌────────────┐   POST /v1/chat/completions   ┌─────────────────────┐
│ API client │ ─────────────────────────────▶│ LLM Gateway         │
│            │◀───────────────────────────── │ FastAPI container   │
└────────────┘   normalized SSE events       └──────────┬──────────┘
                                                       │
                                   ┌───────────────────┴──────────────────┐
                                   │                                      │
                                   ▼                                      ▼
                        ┌─────────────────────┐                ┌─────────────────────┐
                        │ Provider A          │                │ Provider B          │
                        │ Primary             │                │ Backup              │
                        │ /v1/generate        │                │ /chat/stream        │
                        └─────────────────────┘                └─────────────────────┘
```

The Dockerized gateway runs in the supplied DigitalOcean environment.
Provider endpoints remain external HTTP dependencies configured through
environment variables.

## Internal components

### FastAPI application

Responsibilities:

- Create application-scoped configuration and HTTP client dependencies.
- Register the chat-completions route.
- Convert known service failures into sanitized HTTP error responses.
- Close shared resources during application shutdown.

It contains no provider-specific translation or fallback decisions.

### HTTP route

Responsibilities:

- Accept and validate `ChatCompletionRequest`.
- Call the chat-completion service.
- Return either a pre-stream JSON error or `StreamingResponse`.
- Set the public SSE response headers.
- Pass client cancellation through so upstream resources can be closed.

It does not choose providers or parse upstream SSE.

### Public schemas

Responsibilities:

- Define the limited request contract.
- Enforce required fields, supported roles, non-empty content, and
  `stream=true`.
- Reject unknown fields.
- Define normalized content-delta and error payload shapes.

These schemas are independent of both provider formats.

### Chat-completion service

Responsibilities:

- Apply the fixed Provider A then Provider B routing policy.
- Inspect Provider A's HTTP status before creating the downstream response.
- Trigger fallback only for `429`, `502`, and `503`.
- Close Provider A before opening Provider B.
- Prefetch at most the first valid normalized event from the selected provider.
- Return a prepared stream whose upstream lifetime remains valid while FastAPI
  consumes it.
- Convert provider failures into gateway-level exceptions.

This is the only component that decides whether fallback occurs.

### Provider interface

The service depends on one small provider contract implemented by both
adapters. Conceptually, a provider must:

1. Build and open its streaming HTTP request.
2. Expose the upstream HTTP status.
3. Incrementally yield normalized public SSE events.
4. Close its upstream response.

The interface exists because there are two interchangeable provider
implementations. It should not grow into a general plugin framework.

### Provider A adapter

Responsibilities:

- Add Provider A's bearer token.
- Send the configured Provider A model.
- Preserve public message roles and map `messages` directly.
- Send `stream: true`.
- Parse Provider A `data:` events.
- Convert `content_delta` to a normalized content event.
- Convert `done` to the normalized completion event.
- Reject malformed or unknown required event data.

### Provider B adapter

Responsibilities:

- Add Provider B's `X-API-Key`.
- Send the configured Provider B model.
- Translate `messages` into `conversation`.
- Map `user` to `human`; preserve `system` and `assistant`.
- Send `streaming: true`.
- Parse Provider B's named `message` and `done` SSE events.
- Convert provider events to normalized content and completion events.
- Reject malformed or unknown required event data.

### Incremental SSE decoder

Responsibilities:

- Accept arbitrary byte or line boundaries from the HTTP response.
- Accumulate only the current incomplete SSE event.
- Recognize blank-line event boundaries.
- Extract `event` and `data` fields.
- Hand complete events to the provider adapter.

It never accumulates the full model response.

### Configuration

Responsibilities:

- Load Provider A and Provider B base URLs, API keys, and models from
  environment variables.
- Provide the gateway-to-provider model mapping.
- Fail clearly during startup when mandatory configuration is absent.
- Keep secrets out of API responses and logs.

### Outbound HTTP client

An asynchronous streaming HTTP client is shared through application lifetime
and injected into provider adapters. This enables non-blocking reads,
connection reuse, streaming, and deterministic cleanup.

## Dependency direction

```text
FastAPI route
    │
    ▼
Chat-completion service
    │
    ▼
Provider interface
    ├── Provider A adapter ──▶ async HTTP client
    └── Provider B adapter ──▶ async HTTP client

Public schemas ◀── route and service
Configuration ◀── application and provider construction
```

Provider adapters know about public normalized events because they translate
into them. Public schemas and the service do not know Provider A or Provider B
wire formats.

There is no repository layer: repositories would add no value without
persistent state.

## Control flow

### 1. Request validation

```text
Client
  │ POST request
  ▼
FastAPI/Pydantic validation
  ├── invalid ──▶ 422 validation response
  └── valid ────▶ chat-completion service
```

Validation completes before any provider is contacted.

### 2. Primary provider succeeds

1. The route sends the validated request to the service.
2. The service asks the Provider A adapter to open its stream.
3. Provider A translates and sends the upstream request.
4. The service verifies that Provider A returned a successful HTTP status.
5. The adapter parses and normalizes at most the first valid event.
6. The service returns the prepared stream to the route.
7. The route creates `StreamingResponse` with status `200`.
8. The prepared first event is emitted.
9. Remaining events are parsed, normalized, and emitted incrementally.
10. Provider A's `done` event becomes `data: [DONE]`.
11. The upstream response is closed in a `finally` cleanup path.

Only a partial current SSE event and the one prefetched normalized event may be
held in memory.

### 3. Primary provider triggers fallback

```text
Provider A request
  │
  ├── 429 / 502 / 503
  │       │
  │       ▼
  │   close Provider A
  │       │
  │       ▼
  │   open Provider B
  │       ├── usable ──▶ return 200 and stream only Provider B events
  │       └── failure ─▶ close Provider B and return 503
  │
  └── any other failure status ──▶ close Provider A and return 502
```

The service performs this work before returning `StreamingResponse`; therefore
the client never sees Provider A's eligible failure when Provider B succeeds.

### 4. Provider B succeeds after fallback

1. Provider A returns `429`, `502`, or `503`.
2. The service closes Provider A.
3. Provider B translates and sends the request using its own model and role
   mapping.
4. The service verifies Provider B's response and prefetches its first valid
   normalized event.
5. The route returns `200 text/event-stream`.
6. Only normalized Provider B content is emitted.
7. Provider B's `done` event becomes `data: [DONE]`.

No fallback metadata is added to the public response.

### 5. Failure before downstream streaming

Failures discovered while selecting and establishing the usable provider can
still produce normal HTTP errors:

- Public validation failure: `422 validation_error`
- Provider A non-fallback status: `502 upstream_error`
- Malformed first provider event: `502 invalid_upstream_response`
- Provider A eligible failure followed by Provider B failure:
  `503 all_providers_failed`
- Unexpected gateway failure: `500 internal_error`

All opened upstream responses are closed before the error is returned.

### 6. Failure after partial output

```text
200 headers and content already emitted
  │
  ▼
selected provider fails or sends malformed data
  │
  ├── do not attempt fallback
  ├── do not emit a JSON or provider-specific error
  ├── do not emit [DONE]
  ├── close the upstream response
  └── end the downstream stream
```

The gateway cannot change the HTTP status after headers are sent. The absence
of `[DONE]` tells the client that completion was interrupted.

### 7. Client disconnects

1. FastAPI cancels or closes downstream iteration.
2. The stream generator's cleanup path runs.
3. The selected provider response is closed.
4. No backup call is made.

## Resource ownership

- The application owns the shared asynchronous HTTP client.
- Each provider adapter opens an upstream response.
- The service owns provider selection and closes rejected/failing responses.
- The returned stream owns the selected response until downstream iteration
  completes or is cancelled.
- Cleanup uses `finally` semantics so normal completion and exceptional exits
  follow the same resource-release path.

## Concurrency and backpressure

Every API request has independent routing and upstream response state. No
mutable request state is shared between requests.

The downstream generator requests the next upstream event only as FastAPI is
ready to send it. This provides natural backpressure and prevents full-response
buffering.

## Deployment architecture

- One Docker container runs the FastAPI application on DigitalOcean.
- Runtime configuration and provider secrets are injected as environment
  variables.
- The container exposes the application HTTP port.
- No database, worker, queue, cache, or additional service is required.

This is sufficient for the assessment. Horizontal scaling, load balancing,
secret-manager integration, and production observability are deliberately
outside the requested scope.

## Key design decisions

1. **Streaming-only public API:** avoids a second execution and testing path.
2. **Fixed two-provider policy:** satisfies the requirement without a dynamic
   routing framework.
3. **Provider adapters own wire formats:** keeps provider-specific translation
   out of HTTP and routing code.
4. **Service owns fallback:** ensures one component controls provider ordering,
   fallback eligibility, and cleanup.
5. **One-event prefetch:** preserves HTTP error/fallback control before
   downstream headers while avoiding full-response buffering.
6. **No midstream fallback:** prevents duplicated or contradictory output.
7. **No repository or database:** there is no persistent domain state.
8. **Async streaming client:** enables live forwarding without blocking the
   FastAPI event loop.
