from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agency_garden import Decision, default_registry, run
from agency_garden.errors import ConfigurationError, PolicyError, RunBlocked
from agency_garden.policies import ModelPolicy
from agency_garden.report import read_run


def test_invalid_model_action_keeps_usage(experiment, tmp_path):
    class Invalid:
        def decide(self, request):
            return Decision({"contribute": 999}, receipt={"usage": {"input_tokens": 17}})

    registry = default_registry()
    registry.register_policy("invalid", Invalid, version="1", files=[__file__])
    data = experiment.model_dump()
    data["agents"][0]["policy"] = {"kind": "invalid"}
    with pytest.raises(RunBlocked):
        run(type(experiment).model_validate(data), tmp_path, registry=registry)
    assert read_run(tmp_path)["reported_usage"] == {"input_tokens": 17}


def test_failed_response_usage_is_not_lost(experiment, tmp_path):
    class Failed:
        def decide(self, request):
            raise PolicyError("Malformed", receipt={"usage": {"output_tokens": 23}})

    registry = default_registry()
    registry.register_policy("failed", Failed, version="1", files=[__file__])
    data = experiment.model_dump()
    data["agents"][0]["policy"] = {"kind": "failed"}
    with pytest.raises(RunBlocked):
        run(type(experiment).model_validate(data), tmp_path, registry=registry)
    assert read_run(tmp_path)["reported_usage"] == {"output_tokens": 23}


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_sdk_retries_are_explicitly_disabled(monkeypatch, provider):
    constructor = Mock()
    module = SimpleNamespace(OpenAI=constructor, Anthropic=constructor)
    monkeypatch.setenv(f"{provider.upper()}_API_KEY", "test-placeholder")
    monkeypatch.setattr("agency_garden.policies.importlib.import_module", lambda name: module)
    policy = ModelPolicy(provider, model="explicit-model", timeout=17.0)
    policy._get_client()
    assert constructor.call_args.kwargs["max_retries"] == 0
    assert constructor.call_args.kwargs["timeout"] == 17.0


@pytest.mark.parametrize("parameters", [{"strategy": "last"}, {"unrecognised": 1}])
def test_scripted_parameters_cannot_override_strategy(parameters):
    with pytest.raises(ConfigurationError):
        default_registry().policy("first", parameters)


def test_caller_mutation_cannot_change_frozen_run(experiment, tmp_path):
    data = experiment.model_dump()
    data["agents"][0]["policy"] = {"kind": "mutating"}
    original = type(experiment).model_validate(data)
    expected = len(original.seeds)

    class Mutating:
        def decide(self, request):
            original.seeds.clear()
            return Decision(request.actions[0])

    registry = default_registry()
    registry.register_policy("mutating", Mutating, version="1", files=[__file__])
    result = run(original, tmp_path, registry=registry)
    assert result.completed == result.episodes == expected
    assert original.seeds == []
