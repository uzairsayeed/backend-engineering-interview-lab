# LLM Gateway — Implementation Stages

## How this plan will be used

- Implement one stage at a time.
- Before starting a stage, restate its files to create and modify.
- Do not modify files outside that stage's list.
- Finish the evaluation commands before proceeding.
- After each stage, record the actual design decisions and any deviations.
- Stop and fix a failed checkpoint rather than building later stages on it.

The confirmed requirements are defined in:

- `docs/requirements.md`
- `docs/api-contract.md`
- `docs/architecture.md`

## Stage 1 — Project foundation and public contract

### What this stage implements

- Python 3.11 project metadata and dependencies.
- Environment-based provider configuration.
- The strict streaming-only public request schema.
- Normalized public response and error data structures.
- Gateway-level exceptions used by later layers.
- Focused schema tests.

This stage does not make outbound requests and does not expose an HTTP route.

### Files to create

1. `pyproject.toml`
2. `app/__init__.py`
3. `app/config.py`
4. `app/schemas.py`
5. `app/errors.py`
6. `tests/test_schemas.py`

### Files to modify

- None.

### File responsibilities

#### `pyproject.toml`

- Require Python 3.11.
- Declare FastAPI, Uvicorn, HTTPX, and Pydantic runtime dependencies.
- Declare Pytest and the selected async Pytest support as development
  dependencies.
- Configure the test path and async test behavior.

#### `app/__init__.py`

- Mark `app` as a Python package.
- Contain no startup behavior.

#### `app/config.py`

- Load:
  - `PROVIDER_A_BASE_URL`
  - `PROVIDER_A_API_KEY`
  - `PROVIDER_A_MODEL`
  - `PROVIDER_B_BASE_URL`
  - `PROVIDER_B_API_KEY`
  - `PROVIDER_B_MODEL`
- Fail clearly when required configuration is missing.
- Keep provider configuration in one immutable settings object.
- Define the public model as `general-chat` and map it to the two configured
  provider model names.

#### `app/schemas.py`

- Define `ChatMessage`.
- Define `ChatCompletionRequest`.
- Accept only `system`, `user`, and `assistant` roles.
- Require non-empty `model`, non-empty `messages`, and non-empty content.
- Accept only the public model `general-chat`.
- Require the literal boolean `stream=true`.
- Reject unsupported fields.
- Define normalized delta and error response data structures.

#### `app/errors.py`

- Define small gateway exceptions for:
  - `upstream_error`
  - `invalid_upstream_response`
  - `all_providers_failed`
  - `internal_error`
- Carry a safe HTTP status, machine-readable code, and sanitized message.
- Never carry provider response bodies or credentials.

#### `tests/test_schemas.py`

- Verify a valid streaming request.
- Reject missing or unsupported models.
- Reject empty messages.
- Reject unsupported roles and empty content.
- Reject missing or false `stream`.
- Reject unknown fields.

### Dependencies

```text
pyproject.toml
    ├── app/config.py
    ├── app/schemas.py
    ├── app/errors.py
    └── tests/test_schemas.py

tests/test_schemas.py ──▶ app/schemas.py
```

`config.py`, `schemas.py`, and `errors.py` must not depend on FastAPI routes,
provider adapters, or the service layer.

### Design decisions

1. The single supported public model is an explicit allowed value rather than
   accepting arbitrary strings that would all route identically.
2. Provider model names remain configuration details and are never accepted
   from clients.
3. Unknown fields are rejected to prevent silently pretending to support more
   of the OpenAI API.
4. Configuration uses a small application settings object; dynamic
   configuration is out of scope.
5. Gateway exceptions contain only safe public information.

### Design patterns

- **Data Transfer Objects:** Pydantic models define the public boundary.
- **Configuration Object:** one validated settings object is passed to runtime
  components instead of reading environment variables throughout the code.

No repository or persistence pattern is introduced.

### How to evaluate this stage

The project installs, all foundation modules import, valid requests parse, and
invalid requests fail for the documented reasons.

### Commands

```bash
python3.11 --version
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m compileall app
pytest tests/test_schemas.py -q
```

### Stage checkpoint

- All commands exit successfully.
- No HTTP application is expected yet.
- Public validation behavior is locked before provider work begins.

## Stage 2 — Provider adapters and incremental SSE parsing

### What this stage implements

- A minimal common provider contract.
- Incremental SSE event decoding.
- Provider A request translation and event normalization.
- Provider B role/request translation and event normalization.
- Fake-upstream adapter tests with no external calls.

This stage validates both provider boundaries independently of routing and
FastAPI.

### Files to create

1. `app/providers/__init__.py`
2. `app/providers/base.py`
3. `app/sse.py`
4. `app/providers/provider_a.py`
5. `app/providers/provider_b.py`
6. `tests/conftest.py`
7. `tests/test_providers.py`

### Files to modify

- None.

### File responsibilities

#### `app/providers/__init__.py`

- Mark the provider directory as a package.
- Do not implement dynamic registration.

#### `app/providers/base.py`

- Define the minimal provider protocol used by the service.
- Define the upstream stream handle/iterator contract.
- Ensure an opened upstream response can be closed explicitly.
- Keep HTTP status inspection separate from event iteration.

#### `app/sse.py`

- Read upstream lines incrementally.
- Collect only fields for the current SSE event.
- Treat a blank line as the event boundary.
- Support `event:` and `data:` fields.
- Ignore SSE comments if present.
- Never buffer the complete completion.

#### `app/providers/provider_a.py`

- Send `POST {base_url}/v1/generate`.
- Add `Authorization: Bearer ...`.
- Preserve public message roles.
- Map the configured Provider A model.
- Send `stream: true`.
- Normalize `content_delta` and `done`.
- Reject malformed JSON or missing required event fields.

#### `app/providers/provider_b.py`

- Send `POST {base_url}/chat/stream`.
- Add `X-API-Key`.
- Map messages to `conversation`.
- Map `user` to `human`.
- Preserve `system` and `assistant`.
- Map the configured Provider B model.
- Send `streaming: true`.
- Normalize named `message` and `done` events.
- Reject malformed JSON or missing required event fields.

#### `tests/conftest.py`

- Provide deterministic test settings.
- Provide HTTPX fake/mock transport helpers.
- Ensure tests never make real external HTTP calls.

#### `tests/test_providers.py`

- Assert Provider A URL, headers, body, and all role values.
- Assert Provider B URL, headers, body, and role mapping.
- Assert both providers normalize content and completion.
- Assert chunked/multi-line SSE input is decoded incrementally.
- Assert malformed provider data raises the gateway's safe error.

### Dependencies

```text
app/config.py ───────────────▶ provider_a.py
app/config.py ───────────────▶ provider_b.py
app/schemas.py ──────────────▶ providers/base.py
app/sse.py ──────────────────▶ provider_a.py
app/sse.py ──────────────────▶ provider_b.py
providers/base.py ───────────▶ provider_a.py
providers/base.py ───────────▶ provider_b.py
tests/conftest.py ───────────▶ tests/test_providers.py
provider_a.py/provider_b.py ─▶ tests/test_providers.py
```

Neither provider adapter may import FastAPI or contain fallback policy.

### Design decisions

1. Provider-specific authentication and wire formats stay inside adapters.
2. Both adapters produce the same normalized event type.
3. HTTPX mock transport is used instead of a third-party mocking library.
4. The SSE decoder holds only one incomplete event.
5. Unknown or malformed required provider events fail explicitly rather than
   leaking provider data or silently producing corrupt output.

### Design patterns

- **Adapter Pattern:** each provider converts a different external API to one
  internal provider contract.
- **Strategy Pattern:** the service can call either provider through the same
  small contract.
- **Async Iterator:** upstream events are consumed lazily to preserve
  backpressure and bounded memory.

### How to evaluate this stage

Both providers must translate exact requests and normalize fake SSE streams
without opening a network connection.

### Commands

```bash
source .venv/bin/activate
python -m compileall app
pytest tests/test_providers.py -q
pytest tests/test_schemas.py tests/test_providers.py -q
```

### Stage checkpoint

- Both provider adapters pass contract tests.
- Fake upstream requests prove the correct endpoint, headers, model, roles,
  and streaming flag.
- Provider-specific SSE payloads never appear in normalized output.

## Stage 3 — Runnable primary-provider vertical slice

### What this stage implements

- The chat-completion service with Provider A as the selected provider.
- One-event prefetch before downstream response creation.
- The FastAPI route and normalized error handling.
- Application startup, HTTP client lifecycle, and dependency wiring.
- A runnable end-to-end Provider A streaming path.

Fallback is intentionally added in Stage 4 after the primary vertical slice is
working.

### Files to create

1. `app/service.py`
2. `app/api.py`
3. `app/main.py`
4. `tests/test_api.py`

### Files to modify

- None.

### File responsibilities

#### `app/service.py`

- Open Provider A's response.
- Validate the upstream HTTP status.
- Prefetch at most the first valid normalized event.
- Return a prepared async stream that yields the prefetched event and then
  continues incrementally.
- Guarantee upstream cleanup on completion, failure, or cancellation.
- Raise gateway exceptions without importing FastAPI.

#### `app/api.py`

- Expose `POST /v1/chat/completions`.
- Accept the strict request schema.
- Convert the prepared stream to `StreamingResponse`.
- Set:
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `X-Accel-Buffering: no`
- Normalize Pydantic validation errors.
- Convert gateway exceptions raised before streaming into documented JSON
  errors.

#### `app/main.py`

- Create the FastAPI application.
- Load settings.
- Create one application-lifetime `httpx.AsyncClient`.
- Construct providers and service.
- Register the API route/dependencies.
- Close the HTTP client during shutdown.
- Export `app` for Uvicorn.

#### `tests/test_api.py`

For this stage:

- Verify a valid Provider A stream returns `200`.
- Verify the response media type and SSE headers.
- Verify normalized deltas and exactly one `[DONE]`.
- Verify request validation returns normalized `422`.
- Verify an invalid first upstream event returns `502` before SSE starts.

Stage 4 extends this same file with fallback and midstream tests.

### Dependencies

```text
Provider A adapter ──▶ app/service.py
Provider contract ───▶ app/service.py
app/errors.py ────────▶ app/service.py
app/schemas.py ───────▶ app/api.py
app/service.py ───────▶ app/api.py
app/config.py ────────▶ app/main.py
both adapters ────────▶ app/main.py
app/api.py ───────────▶ app/main.py
tests/conftest.py ────▶ tests/test_api.py
app/main.py ──────────▶ tests/test_api.py
```

The route depends on the service. The service does not depend on FastAPI.

### Design decisions

1. The first normalized event is prefetched before `StreamingResponse` is
   returned.
2. Prefetch is limited to one event; the full completion is never accumulated.
3. The application owns the HTTP client; individual requests do not create a
   new connection pool.
4. The selected stream owns its upstream response until iteration finishes.
5. HTTP and validation formatting remain at the API boundary.

### Design patterns

- **Service Layer:** routing and stream orchestration are kept outside the
  route.
- **Dependency Injection:** configuration, HTTP client, providers, and service
  are constructed explicitly.
- **Application Factory/Lifespan:** startup and shutdown own shared resources.

### How to evaluate this stage

The application must be importable and runnable. A fake Provider A response
must travel through the complete stack and reach the client in normalized SSE
format.

### Commands

```bash
source .venv/bin/activate
pytest tests/test_api.py -q -k "primary or validation or invalid"
pytest -q
PROVIDER_A_BASE_URL=http://provider-a.invalid \
PROVIDER_A_API_KEY=test-a-key \
PROVIDER_A_MODEL=test-a-model \
PROVIDER_B_BASE_URL=http://provider-b.invalid \
PROVIDER_B_API_KEY=test-b-key \
PROVIDER_B_MODEL=test-b-model \
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

In a second terminal, verify the process and validation path without contacting
an upstream provider:

```bash
curl -i \
  -H 'Content-Type: application/json' \
  -d '{"model":"general-chat","messages":[{"role":"user","content":"Hello"}],"stream":false}' \
  http://127.0.0.1:8080/v1/chat/completions
```

Expected result: the server remains healthy and returns normalized `422`.

### Vertical checkpoint

This is the first required runnable checkpoint:

```text
fake client request
    → FastAPI validation
    → service
    → Provider A adapter
    → fake upstream SSE
    → normalized downstream SSE
    → [DONE]
```

Do not start fallback work until this complete path passes.

## Stage 4 — Silent fallback and streaming failure semantics

### What this stage implements

- Mandatory Provider A fallback statuses.
- Exactly one Provider B attempt.
- Pre-stream failure mapping.
- Midstream termination behavior.
- Cancellation and cleanup checks.
- Complete mandatory automated coverage.

### Files to create

- None.

### Files to modify

1. `app/service.py`
2. `tests/test_api.py`

`app/api.py` may be modified only if Stage 3 reveals that an already-documented
error cannot be represented by the generic exception handler. Otherwise it
must remain unchanged.

### File responsibilities in this stage

#### `app/service.py`

- Attempt Provider A first.
- On Provider A `429`, `502`, or `503`:
  1. Close Provider A.
  2. Open Provider B.
  3. Prefetch Provider B's first valid event.
  4. Return only Provider B's normalized stream.
- Do not fall back for any other Provider A HTTP status.
- Return `503 all_providers_failed` if Provider B cannot be established.
- Never attempt another provider after Provider B.
- After client-visible output, suppress fallback and terminate without
  emitting `[DONE]`.
- Close all responses in every exit path.

#### `tests/test_api.py`

Add tests for:

- Provider A `429` fallback.
- Provider A `502` fallback.
- Provider A `503` fallback.
- No fallback for another status such as `500`.
- Provider B output contains no Provider A error.
- Provider A eligible failure followed by Provider B failure returns `503`.
- Provider failure after partial output ends without `[DONE]`.
- Upstream resources close after success, fallback, failure, and cancellation.

### Dependencies

```text
Provider A + Provider B
          │
          ▼
   app/service.py
          │
          ▼
     app/api.py
          │
          ▼
 tests/test_api.py
```

Fallback remains a service concern. Provider adapters must not call each other.

### Design decisions

1. Fallback eligibility is the fixed set `{429, 502, 503}`.
2. Provider A is closed before Provider B is opened.
3. Connection failures and timeouts are not added as fallback triggers.
4. Midstream provider switching is prohibited.
5. An interrupted stream ends without `[DONE]`; no non-contract SSE error event
   is invented.
6. Parameterized tests cover the three mandatory statuses without duplicate
   test code.

### Design patterns

- **Fixed Failover Policy:** a small explicit sequence is used instead of a
  generic routing engine or chain framework.
- **Resource Ownership:** `try/finally` cleanup gives each opened stream one
  clear owner.

### How to evaluate this stage

The full mandatory behavior must pass against queued fake upstream responses.
Tests must prove call order and resource closure, not only response text.

### Commands

```bash
source .venv/bin/activate
pytest tests/test_api.py -q -k "fallback"
pytest tests/test_api.py -q -k "midstream or closes or cleanup"
pytest -q
```

### Stage checkpoint

- Provider A success streams normally.
- Each required status silently selects Provider B.
- Non-fallback statuses never call Provider B.
- Both-provider failure returns `503` before downstream SSE starts.
- Midstream failure closes without `[DONE]`.
- No test performs an external network request.

## Stage 5 — Docker, operating documentation, and deployment

### What this stage implements

- A Python 3.11 runtime container.
- Reproducible local run and test instructions.
- Runtime environment-variable documentation.
- Local container verification.
- Deployment and remote smoke testing in the supplied DigitalOcean
  environment.

### Files to create

1. `Dockerfile`
2. `README.md`

### Files to modify

- None initially.
- `README.md` will receive the exact DigitalOcean commands once the target
  type, host/application identifier, and access method are supplied.

### File responsibilities

#### `Dockerfile`

- Use a Python 3.11 base image.
- Install only the project/runtime dependencies needed by the service.
- Copy the application.
- Run Uvicorn on `0.0.0.0` using the platform-provided port when available.
- Keep provider secrets outside the image.

#### `README.md`

- Explain the architecture briefly.
- List all required environment variables.
- Document local installation and tests.
- Document local Uvicorn usage.
- Document Docker build/run commands.
- Include a streaming `curl -N` example.
- Document exact fallback and midstream limitations.
- Record DigitalOcean deployment and smoke-test commands.

### Dependencies

```text
pyproject.toml + app/ ──▶ Dockerfile
all runtime/test files ─▶ README.md commands
Dockerfile ─────────────▶ DigitalOcean deployment
deployed URL ───────────▶ remote smoke test
```

### Design decisions

1. Deployment uses one stateless container.
2. API keys and model configuration are injected at runtime.
3. No database, cache, queue, sidecar, or worker is deployed.
4. The image is tested locally before remote deployment.
5. DigitalOcean-specific commands remain explicitly blocked until the target
   type and access details are known; commands will not be guessed.

### Design patterns

- **Twelve-Factor Configuration:** deployment-specific values and secrets are
  supplied through the environment.
- **Stateless Service:** all request state exists only for the lifetime of the
  stream.

### How to evaluate this stage

The image must build, the container must start with environment configuration,
the test suite must still pass, and the deployed endpoint must emit normalized
SSE ending in `[DONE]` against reachable test providers.

### Local commands

```bash
source .venv/bin/activate
pytest -q
docker build -t llm-gateway:assessment .
docker run --rm \
  -p 8080:8080 \
  -e PROVIDER_A_BASE_URL=http://host.docker.internal:9001 \
  -e PROVIDER_A_API_KEY=test-a-key \
  -e PROVIDER_A_MODEL=test-a-model \
  -e PROVIDER_B_BASE_URL=http://host.docker.internal:9002 \
  -e PROVIDER_B_API_KEY=test-b-key \
  -e PROVIDER_B_MODEL=test-b-model \
  llm-gateway:assessment
```

In another terminal:

```bash
curl -i \
  -H 'Content-Type: application/json' \
  -d '{"model":"general-chat","messages":[{"role":"user","content":"Hello"}],"stream":false}' \
  http://127.0.0.1:8080/v1/chat/completions
```

Expected result: normalized `422`, proving the container and public validation
boundary are running without requiring a real provider.

With supplied reachable fake provider URLs:

```bash
curl -N \
  -H 'Content-Type: application/json' \
  -d '{"model":"general-chat","messages":[{"role":"user","content":"Hello"}],"stream":true}' \
  http://127.0.0.1:8080/v1/chat/completions
```

Expected result: normalized `data:` chunks followed by `data: [DONE]`.

### DigitalOcean commands

The deployment target has not been provided. Before this stage begins, replace
this subsection with exact commands for the supplied target:

1. Authenticate using the provided method.
2. Build or publish `llm-gateway:assessment`.
3. Set the six required provider environment variables as secrets/runtime
   configuration.
4. deploy the container.
5. retrieve the public service URL.
6. run the `curl -N` streaming smoke test against that URL.
7. inspect service logs for startup or upstream errors without exposing
   credentials or prompts.

### Stage checkpoint

- Full test suite passes.
- Local image builds and starts.
- Local validation smoke test passes.
- Remote service starts with runtime configuration.
- Remote streaming smoke test receives normalized chunks and `[DONE]`.

## 150-minute implementation budget

### Stage 1 — 20 minutes

- 8 minutes: project metadata and installation.
- 7 minutes: configuration, schemas, and errors.
- 5 minutes: schema tests and checkpoint.

### Stage 2 — 35 minutes

- 8 minutes: provider contract and SSE decoder.
- 15 minutes: both provider adapters.
- 12 minutes: fake transport and adapter tests.

Cumulative time: 55 minutes.

### Stage 3 — 30 minutes

- 12 minutes: service and one-event prefetch.
- 10 minutes: API, application wiring, and error handler.
- 8 minutes: primary vertical-slice tests and runnable checkpoint.

Cumulative time: 85 minutes.

### Stage 4 — 33 minutes

- 13 minutes: fallback and cleanup behavior.
- 15 minutes: mandatory fallback/midstream tests.
- 5 minutes: full-suite fixes.

Cumulative time: 118 minutes.

### Stage 5 — 32 minutes

- 6 minutes: Dockerfile.
- 5 minutes: README and operating commands.
- 7 minutes: local image build and smoke test.
- 10 minutes: DigitalOcean deployment.
- 4 minutes: remote smoke test and delivery verification.

Total: 150 minutes.

The separate final review period remains 30 minutes.

## Fallback plan if time runs short

### Non-negotiable scope

Do not drop:

- Streaming-only public endpoint.
- Strict request validation.
- Both provider translations.
- Incremental SSE normalization.
- Provider A first.
- Fallback for `429`, `502`, and `503`.
- Exactly one Provider B attempt.
- One-event prefetch before downstream headers.
- No unsafe midstream fallback.
- Upstream cleanup.
- Meaningful mocked tests.
- Docker and deployment attempt.

### If behind at 55 minutes

- Stop polishing type aliases and comments.
- Keep the provider interface to the minimum methods required by the service.
- Use HTTPX's built-in mock transport; add no test libraries.
- Do not implement optional timeout/connection fallback.

### If behind at 85 minutes

- Do not refactor the working Provider A vertical slice.
- Implement fallback as one explicit conditional flow.
- Parameterize the three required fallback statuses.
- Retain the required provider-independent `/health` endpoint, but add no
  additional public business endpoints or request fields.

### If behind at 110 minutes

Retain these tests first:

1. Request validation.
2. Provider A translation and successful stream.
3. Provider B translation and successful normalization.
4. Parameterized `429/502/503` fallback.
5. Non-fallback status.
6. Both providers fail.
7. Midstream interruption has no `[DONE]`.

Defer only additional duplicate edge-case tests, never the mandatory behaviors.

### If behind at 125 minutes

- Freeze application refactoring.
- Create the minimal Dockerfile.
- Run the full suite once.
- Build the image.
- Move directly to deployment.
- Add only the README commands needed to run, test, and explain limitations.

### If deployment access is still unavailable

- Verify the image locally.
- Record the exact missing target/access information.
- Prepare but do not invent platform commands.
- Deploy immediately when credentials and target details arrive.

### Shortcuts that are not allowed

- Buffering the complete provider response.
- Returning provider-specific events.
- Logging API keys or prompts.
- Falling back after partial client-visible output.
- Removing response cleanup.
- Calling real providers from automated tests.
- Adding unrelated infrastructure.
