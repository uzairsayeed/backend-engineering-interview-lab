"""Tests for the limited public API contract."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    ChatCompletionRequest,
    ContentDelta,
    ContentDeltaChunk,
    ErrorBody,
    ErrorResponse,
    StreamChoice,
)


def valid_request_data() -> dict[str, object]:
    return {
        "model": "general-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }


def test_accepts_valid_streaming_request() -> None:
    request = ChatCompletionRequest.model_validate(valid_request_data())

    assert request.model == "general-chat"
    assert request.messages[0].role == "user"
    assert request.messages[0].content == "Hello"
    assert request.stream is True


@pytest.mark.parametrize("model", ["provider-a-model", "unknown", ""])
def test_rejects_unsupported_model(model: str) -> None:
    data = valid_request_data()
    data["model"] = model

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(data)


def test_rejects_missing_model() -> None:
    data = valid_request_data()
    del data["model"]

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(data)


def test_rejects_empty_messages() -> None:
    data = valid_request_data()
    data["messages"] = []

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(data)


@pytest.mark.parametrize("role", ["tool", "developer", "human"])
def test_rejects_unsupported_message_role(role: str) -> None:
    data = valid_request_data()
    data["messages"] = [{"role": role, "content": "Hello"}]

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(data)


@pytest.mark.parametrize("content", ["", " ", "\n\t"])
def test_rejects_empty_or_blank_message_content(content: str) -> None:
    data = valid_request_data()
    data["messages"] = [{"role": "user", "content": content}]

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(data)


@pytest.mark.parametrize("stream", [False, None, "true"])
def test_rejects_values_other_than_boolean_true_for_stream(
    stream: object,
) -> None:
    data = valid_request_data()
    data["stream"] = stream

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(data)


def test_rejects_missing_stream() -> None:
    data = valid_request_data()
    del data["stream"]

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(data)


def test_rejects_unknown_request_field() -> None:
    data = valid_request_data()
    data["temperature"] = 0.5

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(data)


def test_rejects_unknown_message_field() -> None:
    data = valid_request_data()
    data["messages"] = [
        {"role": "user", "content": "Hello", "provider": "provider-a"}
    ]

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(data)


def test_content_delta_chunk_matches_public_shape() -> None:
    chunk = ContentDeltaChunk(
        choices=[StreamChoice(delta=ContentDelta(content="Hello"))]
    )

    assert chunk.model_dump() == {
        "choices": [{"index": 0, "delta": {"content": "Hello"}}]
    }


def test_error_response_omits_optional_details_when_serialized() -> None:
    response = ErrorResponse(
        error=ErrorBody(
            code="upstream_error",
            message="The upstream provider could not process the request.",
        )
    )

    assert response.model_dump(exclude_none=True) == {
        "error": {
            "code": "upstream_error",
            "message": "The upstream provider could not process the request.",
        }
    }
