import pytest

from agency_garden import AgentConfig, Experiment, PolicyConfig, WorldConfig


@pytest.fixture
def experiment():
    return Experiment(
        name="test-garden",
        world=WorldConfig(parameters={"rounds": 2}),
        agents=[
            AgentConfig(id="ada", policy=PolicyConfig(kind="middle")),
            AgentConfig(id="basil", policy=PolicyConfig(kind="last")),
        ],
        seeds=[7, 11],
    )
