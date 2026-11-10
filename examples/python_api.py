"""Run offline: python examples/python_api.py --output runs/python-example."""

import argparse

from agency_garden import AgentConfig, Condition, Experiment, PolicyConfig, WorldConfig, run
from agency_garden.report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="runs/python-example")
    args = parser.parse_args()
    experiment = Experiment(
        name="reciprocity",
        world=WorldConfig(kind="trust", parameters={"rounds": 5}),
        agents=[
            AgentConfig(id="ada", policy=PolicyConfig(kind="middle")),
            AgentConfig(id="basil", policy=PolicyConfig(kind="random")),
        ],
        seeds=[11, 22, 33],
        conditions=[
            Condition(name="baseline", world={"multiplier": 2}),
            Condition(name="greater-return", world={"multiplier": 3}),
        ],
    )
    result = run(experiment, args.output)
    _, page = write_report(result.directory)
    print(f"Completed {result.completed}/{result.episodes} episodes. Open {page}")


if __name__ == "__main__":
    main()
