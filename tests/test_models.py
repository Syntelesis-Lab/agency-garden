from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agency_garden import Request
from agency_garden.errors import ConfigurationError, PolicyError
from agency_garden.policies import ModelPolicy, parse_model_response


@pytest.fixture
def request_packet():
    return Request("ada", 0, 1, {"world": "example"}, ({"choose": 1},))


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_provider_contract_with_mocked_sdk(provider, request_packet):
    policy = ModelPolicy(provider, model="explicit-test-model")
    client = Mock()
    policy._client = client
    body = '{"action":{"choose":1},"memory":{},"reason":null}'
    usage = Mock()
    usage.model_dump.return_value = {"input_tokens": 20, "output_tokens": 10}
    if provider == "openai":
        client.responses.create.return_value = SimpleNamespace(
            output_text=body, status="completed", id="r1", model="resolved-model", usage=usage
        )
    else:
        client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type="text", text=body)],
            stop_reason="end_turn",
            id="r1",
            model="resolved-model",
            usage=usage,
        )
    decision = policy.decide(request_packet)
    assert decision.action == {"choose": 1}
    assert decision.receipt["response_model"] == "resolved-model"
    assert decision.receipt["usage"]["input_tokens"] == 20
    method = client.responses.create if provider == "openai" else client.messages.create
    assert method.call_count == 1
    assert method.call_args.kwargs["model"] == "explicit-test-model"


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        "{}",
        "[]",
        '{"action":{},"memory":[],"reason":null}',
        '{"action":{},"memory":{},"reason":1}',
        '{"action":{"x":NaN},"memory":{},"reason":null}',
    ],
)
def test_invalid_response_preserves_receipt(body):
    with pytest.raises(PolicyError) as error:
        parse_model_response(body, {"text": body})
    assert error.value.receipt == {"text": body}


def test_incomplete_response_is_not_an_action(request_packet):
    policy = ModelPolicy("openai", model="example")
    policy._client = Mock()
    policy._client.responses.create.return_value = SimpleNamespace(
        output_text="{}", status="incomplete", id="r", usage=None
    )
    with pytest.raises(PolicyError, match="did not complete") as error:
        policy.decide(request_packet)
    assert error.value.receipt["status"] == "incomplete"


def test_provider_error_does_not_echo_secrets(request_packet):
    policy = ModelPolicy("openai", model="example")
    policy._client = Mock()
    policy._client.responses.create.side_effect = RuntimeError("secret-from-provider")
    with pytest.raises(PolicyError) as error:
        policy.decide(request_packet)
    assert "secret-from-provider" not in str(error.value.receipt)
    assert policy._client.responses.create.call_count == 1


def test_no_key_fails_before_any_call(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        ModelPolicy("openai", model="example").check_available()
