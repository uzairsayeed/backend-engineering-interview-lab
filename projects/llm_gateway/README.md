# LLM Gateway

A small FastAPI service that exposes one streaming chat-completion API over
two fictional HTTP providers. It translates the public request into each
provider's format, normalizes provider SSE events, and silently falls back from
Provider A to Provider B for the required pre-stream failures.

## Problem scope

The gateway implements:

- `POST /v1/chat/completions`
- `GET /health` for provider-independent platform health checks
- A limited OpenAI-compatible request and SSE response
- Streaming requests only (`stream=true`)
- Provider A as primary and Provider B as backup
- Incremental SSE parsing without complete-response buffering
- Silent fallback for Provider A HTTP `429`, `502`, and `503`
- Sanitized public errors
- Mocked automated tests with no real provider calls
- A Python 3.11 Docker image

The only public model is `general-chat`. Provider-specific model names remain
internal configuration.

## Architecture

```text
Client
  │ POST /v1/chat/completions
  ▼
FastAPI route and Pydantic validation
  ▼
ChatCompletionService
  ├── Provider A adapter ──▶ Provider A /v1/generate
  └── Provider B adapter ──▶ Provider B /chat/stream
  ▼
Normalized ContentEvent / DoneEvent
  ▼
Public text/event-stream response
```

Responsibilities are separated as follows:

- `app/schemas.py`: public request, stream, and error schemas
- `app/api.py`: HTTP validation, error mapping, and public SSE serialization
- `app/service.py`: provider ordering, fallback, prefetch, and cleanup
- `app/providers/`: provider-specific authentication and translation
- `app/sse.py`: provider-independent incremental SSE framing
- `app/main.py`: settings, shared HTTPX client, and application lifecycle

The service prefetches at most one normalized provider event before returning
the downstream streaming response. This preserves the ability to return a
normal HTTP error or fall back before client-visible output without buffering
the full completion.

More detail is available in:

- `docs/requirements.md`
- `docs/api-contract.md`
- `docs/architecture.md`

## Environment variables

The application listens on `PORT`, defaulting to `8080`.

All six provider variables are required at application startup:

- `PROVIDER_A_BASE_URL`: Provider A base URL, without the endpoint path
- `PROVIDER_A_API_KEY`: Provider A bearer token
- `PROVIDER_A_MODEL`: model sent to Provider A
- `PROVIDER_B_BASE_URL`: Provider B base URL, without the endpoint path
- `PROVIDER_B_API_KEY`: Provider B `X-API-Key` value
- `PROVIDER_B_MODEL`: model sent to Provider B

Create a local environment file from the tracked template:

```bash
cp .env.example .env
```

Replace every placeholder in `.env` before making a valid streaming request.

Example:

```bash
export PROVIDER_A_BASE_URL=https://provider-a.example
export PROVIDER_A_API_KEY=replace-me
export PROVIDER_A_MODEL=provider-a-model
export PROVIDER_B_BASE_URL=https://provider-b.example
export PROVIDER_B_API_KEY=replace-me
export PROVIDER_B_MODEL=provider-b-model
```

Provider API keys and prompt content are not included in gateway-generated
errors or intentional application logs.

## Local setup and run

Requirements:

- Python 3.11

Create the environment and install the application:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Export the required environment variables, then start the server. The local
command uses `8080` unless `PORT` is already set:

```bash
uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8080}"
```

API documentation is available at:

```text
http://127.0.0.1:8080/docs
```

Process health can be checked without contacting either provider:

```bash
curl http://127.0.0.1:8080/health
```

Expected output:

```json
{"status":"ok"}
```

## API example

The endpoint supports only the documented public model and streaming mode:

```bash
curl --no-buffer \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "general-chat",
    "messages": [
      {
        "role": "user",
        "content": "Explain containers."
      }
    ],
    "stream": true
  }' \
  http://127.0.0.1:8080/v1/chat/completions
```

Example successful output:

```text
data: {"choices":[{"index":0,"delta":{"content":"Containers"}}]}

data: {"choices":[{"index":0,"delta":{"content":" isolate applications."}}]}

data: [DONE]

```

`curl --no-buffer` displays events as they arrive instead of waiting for curl
to buffer output.

## Tests

Run the complete suite:

```bash
source .venv/bin/activate
pytest -q
```

Run the provider translation tests:

```bash
pytest tests/test_providers.py -q
```

Run the fallback tests:

```bash
pytest tests/test_api.py -q \
  -k "falls_back or both_providers or invalid_backup"
```

Run the midstream and cleanup tests:

```bash
pytest tests/test_api.py -q \
  -k "partial_output or disconnect or stopping_downstream"
```

Run the explicit no-buffering test:

```bash
pytest tests/test_api.py -q -k "incrementally"
```

The no-buffering test verifies:

1. Stream preparation consumes exactly one upstream event.
2. Emitting that prefetched event consumes no additional events.
3. Requesting the next downstream event consumes exactly one more upstream
   event.

All provider HTTP calls use HTTPX mock transports. Automated tests require no
credentials and make no real external requests.

## Docker

Build the image:

```bash
docker build -t llm-gateway:assessment .
```

Run it:

```bash
docker run --rm \
  --env-file .env \
  -e PORT=8080 \
  -p 8080:8080 \
  llm-gateway:assessment
```

The container:

- Uses Python 3.11
- Runs as a non-root user
- Listens on `PORT` when supplied, otherwise port `8080`
- Receives all provider configuration at runtime
- Contains no provider credentials

For a startup smoke test without calling reachable providers:

```bash
curl -i http://127.0.0.1:8080/health
```

Expected result: `200 OK` with `{"status":"ok"}`. A successful `stream=true`
smoke test requires reachable fictional provider endpoints.

## Fallback behavior

The routing policy is fixed:

```text
Call Provider A
  ├── 2xx: stream Provider A
  ├── 429/502/503 before output:
  │     close Provider A
  │     call Provider B once
  │       ├── success: stream only Provider B
  │       └── failure: return 503 all_providers_failed
  └── any other HTTP failure: return 502 upstream_error
```

Connection failures are normalized to `502 upstream_error` but do not trigger
fallback.

Fallback is not attempted after client-visible content. Switching providers at
that point could duplicate or contradict the partial answer. A midstream
failure closes the response without emitting `[DONE]`.

## HTTP timeouts

The shared outbound HTTPX client uses finite timeouts:

- Connect: 5 seconds
- Read: 60 seconds
- Write: 10 seconds
- Connection-pool acquisition: 5 seconds

The read timeout is intentionally longer because streamed LLM tokens may have
variable inter-chunk latency. Connection and pool waits remain short and
bounded.

## Known limitations

- Only `model="general-chat"` is accepted.
- Only `stream=true` is supported.
- Only text messages with `system`, `user`, and `assistant` roles are
  supported.
- There is no model-discovery endpoint.
- There are exactly two providers and one backup attempt.
- Midstream fallback is not supported.
- Connection failures and timeouts do not trigger fallback.
- An interrupted stream is indicated by the absence of `[DONE]`; there is no
  custom SSE error event.
- There is no authentication, database, persistence, rate limiting, caching,
  queue, circuit breaker, or usage accounting.
- Provider integrations are fictional and automated tests use mocked upstream
  responses.

## DigitalOcean deployment

Do not create or modify a DigitalOcean resource until a specific App Platform
application or Droplet has been assigned.

### App Platform

When an App Platform application is assigned:

1. Connect this repository and select Dockerfile-based deployment.
2. Configure the service HTTP port as `8080`.
3. Configure the health-check path as `/health`.
4. Keep the Dockerfile run command:

   ```text
   uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
   ```

5. Add `PORT=8080` as a runtime environment variable.
6. Add all six `PROVIDER_*` values as encrypted runtime secrets.
7. Deploy only to the assigned application.
8. Verify process health:

   ```bash
   curl -i "https://<assigned-app-domain>/health"
   ```

9. After provider credentials are supplied, run the `curl --no-buffer`
   chat-completion example against the assigned domain and confirm `[DONE]`.

### Docker-capable Droplet

When a Droplet and access method are assigned:

1. Connect to the assigned Droplet and ensure Docker is installed.
2. Obtain the repository or pull its prebuilt image.
3. Create a local `.env` file containing the six real provider values. Do not
   copy this file into the image.
4. If building on the Droplet:

   ```bash
   docker build -t llm-gateway:assessment .
   ```

5. Run the service:

   ```bash
   docker run -d \
     --name llm-gateway \
     --restart unless-stopped \
     --env-file .env \
     -e PORT=8080 \
     -p 8080:8080 \
     llm-gateway:assessment
   ```

6. Allow inbound port `8080` only through the assigned firewall or reverse
   proxy configuration.
7. Verify health:

   ```bash
   curl -i http://<assigned-droplet-address>:8080/health
   ```

8. If an nginx reverse proxy is used, disable proxy buffering for
   `/v1/chat/completions` so SSE events remain live.
9. After provider credentials are supplied, run the `curl --no-buffer`
   chat-completion example and confirm `[DONE]`.

Deployment URL:

```text
Pending — no specific App Platform application or Droplet has been assigned,
and real provider configuration has not yet been supplied.
```
