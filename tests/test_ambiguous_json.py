import pytest

from agency_garden.config import load_experiment
from agency_garden.errors import ConfigurationError, PolicyError
from agency_garden.policies import parse_model_response


@pytest.mark.parametrize(
    "body",
    [
        '{"action":{"contribute":0},"action":{"contribute":10},"memory":{},"reason":null}',
        '{"action":{"contribute":0,"contribute":10},"memory":{},"reason":null}',
        '{"action":{"contribute":0},"memory":{"goal":"one","goal":"two"},"reason":null}',
    ],
)
def test_ambiguous_decisions_fail_and_keep_original_response(body):
    receipt = {"text": body, "usage": {"output_tokens": 20}}
    with pytest.raises(PolicyError) as error:
        parse_model_response(body, receipt)
    assert error.value.receipt == receipt


def test_duplicate_configuration_keys_fail(tmp_path):
    path = tmp_path / "experiment.json"
    path.write_text('{"name":"one","name":"two","agents":[{"id":"ada"},{"id":"basil"}]}')
    with pytest.raises(ConfigurationError, match="Duplicate JSON key"):
        load_experiment(path)
