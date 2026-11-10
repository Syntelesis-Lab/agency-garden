# Python API

The configuration models and extension contracts are exported from `agency_garden`. Interfaces are provisional during the alpha series. Consult the type annotations in the installed package for full signatures.

## Configure and run

```python
from agency_garden import AgentConfig, Experiment, PolicyConfig, WorldConfig, run
from agency_garden.report import read_run, write_report

experiment = Experiment(
    name="small-garden",
    world=WorldConfig(kind="trust", parameters={"rounds": 3}),
    agents=[
        AgentConfig(id="ada", policy=PolicyConfig(kind="middle")),
        AgentConfig(id="basil", policy=PolicyConfig(kind="random")),
    ],
    seeds=[11, 22, 33],
)
result = run(experiment, "runs/small-garden")
json_path, html_path = write_report(result.directory)
data = read_run(result.directory)
assert data["completed"] == 3
```

| Name | Purpose |
|---|---|
| `Experiment` | Validated design: world, participants, seeds, conditions, repetitions and limits |
| `WorldConfig(kind, parameters)` | World implementation and base parameters |
| `AgentConfig(id, policy, instructions)` | Participant identity and instructions |
| `PolicyConfig(kind, parameters)` | Scripted, model or custom policy |
| `Condition(name, world, policies)` | World parameter overrides and per-agent policy replacements |
| `Limits(max_steps, max_decisions)` | Per-episode steps and whole-run decision attempts |
| `run(experiment, output, registry=None, retry_failed=False)` | Create or resume a compatible run |
| `RunResult` | Resolved directory, fingerprint, completed/total episodes and attempts |

`load_experiment(path)` from `agency_garden.config` reads TOML or JSON. `Experiment.model_json_schema()` describes the configuration structure. Unknown fields and invalid types fail validation.

`run` returns only after all episodes complete. It raises `RunBlocked` for a failed or uncertain decision or a reached limit. Read the saved report to inspect partial evidence. Resume with the same experiment and output directory; changing the configuration requires a new directory.

## Extensions

`World`, `Policy`, `Request` and `Decision` are small typed contracts. A `Request` contains only the actor's projected observation, legal action menu, persisted memory, instructions and a deterministic request seed. A `Decision` contains action, memory, optional reason and a receipt.

`default_registry()` returns built-ins. `Registry()` starts empty. Register a world or policy with its factory, explicit version, source files and dependency distribution names. Pass the registry to `run`. See [Extensions](extensions.md) for complete examples and determinism requirements.

## Reports and errors

`read_run(directory, include_private=False)` verifies a consistent database snapshot and returns a JSON-compatible dictionary. `write_report` returns the paths of JSON and self-contained HTML files. Private exports use distinct `.private` filenames.

Catch `GardenError` from `agency_garden.errors` for engine errors. Its subclasses distinguish invalid configuration, evidence inconsistency, policy failure and blocked execution. Normal Python I/O errors can also propagate through the Python API; the CLI formats these as errors with exit code 2. Ctrl-C exits the CLI with 130.
